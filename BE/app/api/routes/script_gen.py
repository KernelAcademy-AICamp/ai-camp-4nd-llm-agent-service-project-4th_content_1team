"""
Script Generation API Router

스크립트 생성 워크플로우를 시작하고 관리하는 API 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool  # run_in_threadpool 임포트
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.core.db import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.script_gen import (
    ScriptGenStartRequest,
    ScriptGenStartResponse,
    ScriptGenPlannerResponse,
    PlannerInputResponse,
    ChannelProfileResponse,
    TopicContextResponse,
    ScriptGenExecuteResponse, 
    ScriptGenTaskResponse,
)

from src.script_gen.utils.input_builder import (
    build_planner_input,
    PlannerInputBuildError,
)
from src.script_gen.nodes.planner import planner_node
from src.script_gen.graph import generate_script  # Import generate_script

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/script-gen", tags=["script-generation"])


# =============================================================================
# Endpoints
# =============================================================================

from celery.result import AsyncResult
from app.worker import task_generate_script  # Celery Task 임포트


# ... (기존 impor 생략)

# =============================================================================
# Async Endpoints (Celery)
# =============================================================================

@router.post("/execute", response_model=ScriptGenTaskResponse)
async def execute_pipeline_async(
    request: ScriptGenStartRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    [비동기] 전체 파이프라인 실행 요청
    
    1. 작업을 백그라운드 큐(Celery)에 등록하고 즉시 task_id를 반환합니다.
    2. 클라이언트는 task_id를 사용하여 /status/{task_id}를 폴링해야 합니다.
    """
    logger.info(f"Queueing async pipeline for: {request.topic}")
    
    try:
        # 1. Planner Input 빌드 (DB 조회 등은 여기서 수행)
        planner_input = await build_planner_input(
            db=db,
            topic=request.topic,
            user_id=str(current_user.id),
            topic_recommendation_id=request.topic_recommendation_id,
        )
        
        # 2. topic_context를 channel_profile에 병합
        # (Planner가 channel_profile.topic_context에서 추천 컨텍스트를 읽음)
        channel_profile = planner_input["channel_profile"].copy()
        if planner_input.get("topic_context"):
            channel_profile["topic_context"] = planner_input["topic_context"]
        
        # 3. Celery Task 실행 (.delay() 사용)
        # user_id, channel_id를 전달하여 DB에 결과 저장
        task = task_generate_script.delay(
            topic=planner_input["topic"],
            channel_profile=channel_profile,
            topic_request_id=None,
            user_id=str(current_user.id),
            channel_id=channel_profile.get("channel_id"),
        )
        
        return ScriptGenTaskResponse(
            task_id=task.id,
            status="PENDING",
            result=None
        )
        
    except Exception as e:
        logger.error(f"Failed to queue task: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"작업 요청 실패: {str(e)}"
        )


@router.get("/status/{task_id}", response_model=ScriptGenTaskResponse)
async def get_task_status(task_id: str):
    """
    [비동기] 작업 상태 및 결과 조회
    """
    try:
        task_result = AsyncResult(task_id)
        
        response = ScriptGenTaskResponse(
            task_id=task_id,
            status=task_result.status
        )
        
        if task_result.state == 'SUCCESS':
            # task_result.result는 worker가 반환한 dict
            result_data = task_result.result
            response.result = ScriptGenExecuteResponse(**result_data)
            
        elif task_result.state == 'FAILURE':
            response.result = ScriptGenExecuteResponse(
                success=False,
                message="Celery Task Failure",
                error=str(task_result.result)
            )
            
        return response
        
    except Exception as e:
        logger.error(f"Status check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"상태 조회 실패: {str(e)}"
        )


@router.post("/run-complete", response_model=ScriptGenExecuteResponse)
async def run_complete_pipeline(
    request: ScriptGenStartRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    [통합 테스트용] 전체 파이프라인 실행 및 최종 결과 반환
    
    주의: 실행 시간이 깁니다 (30-60초). 
    동기 함수를 스레드풀에서 실행하여 이벤트 루프 차단을 방지합니다.
    """
    logger.info(f"Starting full pipeline execution for: {request.topic}")
    
    try:
        # 1. Planner Input 빌드 (채널 프로필 등 가져오기)
        planner_input = await build_planner_input(
            db=db,
            topic=request.topic,
            user_id=str(current_user.id),
            topic_recommendation_id=request.topic_recommendation_id,
        )
        
        # 2. 비동기 파이프라인 실행
        # generate_script는 async 함수이므로 직접 await
        result_dict = await generate_script(
            topic=planner_input["topic"],
            channel_profile=planner_input["channel_profile"],
            topic_request_id=None
        )
        
        # 3. 결과 매핑 (Dict -> Pydantic Schema)
        script_obj = result_dict.get("script", {})
        
        # 3-1. Script 매핑
        final_script = None
        if script_obj:
            chapters = []
            for ch in script_obj.get("chapters", []):
                # Beat 등을 합쳐서 하나의 텍스트로 (또는 narration 필드 사용)
                content = ch.get("narration", "")
                if not content:
                    # narration이 비어있으면 beat line을 합침
                    beats = ch.get("beats", [])
                    content = "\n".join([b.get("line", "") for b in beats])
                
                chapters.append({
                    "title": ch.get("title", ""),
                    "content": content
                })
                
            final_script = {
                "hook": script_obj.get("hook", {}).get("text", ""),
                "chapters": chapters,
                "outro": script_obj.get("closing", {}).get("text", "")
            }
            
        # 3-2. References 매핑 (News Research 결과 활용)
        references = [] 
        news_data = result_dict.get("news_data", {})
        articles = news_data.get("articles", [])
        
        for art in articles:
            # 기사 데이터 유효성 검사 및 매핑
            if art.get("title") and art.get("url"):
                references.append({
                    "title": art.get("title"),
                    "summary": art.get("summary_short") or art.get("summary", "")[:100] + "...",
                    "source": art.get("source", "Unknown"),
                    "url": art.get("url"),
                    "date": art.get("pub_date")
                })
        
        return ScriptGenExecuteResponse(
            success=True,
            message="전체 파이프라인 실행 완료",
            script=final_script,
            references=references 
        )

    except Exception as e:
        logger.error(f"Full pipeline execution failed: {e}", exc_info=True)
        return ScriptGenExecuteResponse(
            success=False,
            message="실행 중 오류 발생",
            error=str(e)
        )


@router.post("/start", response_model=ScriptGenStartResponse)
async def start_script_generation(
    request: ScriptGenStartRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    스크립트 생성 워크플로우 시작
    
    1. Planner 입력 데이터 생성 (DB 조회 + 매핑)
    2. 비동기 작업 시작 (향후 구현)
    3. task_id 반환
    
    현재는 동기 방식으로 Planner 입력만 생성하여 반환합니다.
    """
    
    try:
        # Planner 입력 생성
        planner_input = await build_planner_input(
            db=db,
            topic=request.topic,
            user_id=str(current_user.id),
            topic_recommendation_id=request.topic_recommendation_id,
        )
        
        logger.info(
            f"Planner input built for user {current_user.id}, "
            f"topic: {request.topic}"
        )
        
        # 응답 변환 (디버깅용)
        planner_input_response = _convert_planner_input_to_response(planner_input)
        
        return ScriptGenStartResponse(
            success=True,
            message="스크립트 생성 준비가 완료되었습니다.",
            task_id=None,  # 향후 비동기 작업 ID
            planner_input=planner_input_response,
        )
    
    except PlannerInputBuildError as e:
        # 사용자 친화적 에러 (400)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    except Exception as e:
        # 예상치 못한 에러 (500)
        logger.error(f"Unexpected error in start_script_generation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="스크립트 생성 준비 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
        )


@router.post("/planner", response_model=ScriptGenPlannerResponse)
async def run_planner(
    request: ScriptGenStartRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Planner 노드만 실행 (테스트/디버깅용)
    
    1. Planner 입력 생성
    2. Planner 노드 실행
    3. ContentBrief 반환
    """
    
    try:
        # 1. Planner 입력 생성
        planner_input = await build_planner_input(
            db=db,
            topic=request.topic,
            user_id=str(current_user.id),
            topic_recommendation_id=request.topic_recommendation_id,
        )
        
        logger.info(f"Running planner for topic: {request.topic}")
        
        # 2. Planner 노드 실행
        # State 구성 (Planner가 필요로 하는 최소 state)
        # topic_context를 channel_profile에 병합
        channel_profile_with_context = planner_input["channel_profile"].copy()
        if planner_input.get("topic_context"):
            channel_profile_with_context["topic_context"] = planner_input["topic_context"]
        
        state = {
            "topic": planner_input["topic"],
            "channel_profile": channel_profile_with_context,
            "trend_analysis": None,  # Trend Scout 없이 실행
        }
        
        # Planner 실행
        result = planner_node(state)
        
        logger.info("Planner execution completed successfully")
        
        return ScriptGenPlannerResponse(
            success=True,
            message="콘텐츠 기획안이 생성되었습니다.",
            content_brief=result.get("content_brief"),
            error=None,
        )
    
    except PlannerInputBuildError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    except Exception as e:
        logger.error(f"Error in run_planner: {e}", exc_info=True)
        return ScriptGenPlannerResponse(
            success=False,
            message="콘텐츠 기획안 생성에 실패했습니다.",
            content_brief=None,
            error=str(e),
        )


# =============================================================================
# History Endpoint (새로고침 후 결과 조회)
# =============================================================================

from sqlalchemy import select, desc


@router.get("/scripts/history")
async def get_script_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 10,
):
    """
    사용자의 생성 이력 조회 (새로고침해도 결과 유지)
    """
    from app.models.topic_request import TopicRequest
    from app.models.script_output import VerifiedScript

    try:
        # TopicRequest + VerifiedScript 조인 조회
        stmt = (
            select(TopicRequest, VerifiedScript)
            .outerjoin(VerifiedScript, TopicRequest.id == VerifiedScript.topic_request_id)
            .where(TopicRequest.user_id == current_user.id)
            .order_by(desc(TopicRequest.created_at))
            .limit(limit)
        )
        rows = (await db.execute(stmt)).all()

        results = []
        for topic_req, verified in rows:
            item = {
                "topic_request_id": str(topic_req.id),
                "topic_title": topic_req.topic_title,
                "status": topic_req.status,
                "created_at": topic_req.created_at.isoformat() if topic_req.created_at else None,
                "script": None,
                "references": None,
                "competitor_videos": None,
            }
            if verified:
                item["script"] = verified.final_script_json
                source_map = verified.source_map_json or {}
                item["references"] = source_map.get("references", [])
                item["competitor_videos"] = source_map.get("competitor_videos", [])
            results.append(item)

        return {"success": True, "results": results}

    except Exception as e:
        logger.error(f"History fetch failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"이력 조회 실패: {str(e)}",
        )


@router.get("/scripts/{topic_request_id}")
async def get_script_by_id(
    topic_request_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    특정 스크립트 결과 조회
    """
    from app.models.topic_request import TopicRequest
    from app.models.script_output import VerifiedScript
    from uuid import UUID as PyUUID

    # URL에서 받은 str → UUID 변환 (잘못된 값이면 400 에러)
    try:
        topic_uuid = PyUUID(topic_request_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="유효하지 않은 ID 형식입니다.")

    try:
        stmt = (
            select(TopicRequest, VerifiedScript)
            .outerjoin(VerifiedScript, TopicRequest.id == VerifiedScript.topic_request_id)
            .where(TopicRequest.id == topic_uuid)
            .where(TopicRequest.user_id == current_user.id)
        )
        row = (await db.execute(stmt)).first()

        if not row:
            raise HTTPException(status_code=404, detail="결과를 찾을 수 없습니다.")

        topic_req, verified = row
        result = {
            "success": True,
            "topic_request_id": str(topic_req.id),
            "topic_title": topic_req.topic_title,
            "status": topic_req.status,
            "script": None,
            "references": None,
            "competitor_videos": None,
        }
        if verified:
            result["script"] = verified.final_script_json
            source_map = verified.source_map_json or {}
            result["references"] = source_map.get("references", [])
            result["competitor_videos"] = source_map.get("competitor_videos", [])

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Script fetch failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"결과 조회 실패: {str(e)}",
        )


# =============================================================================
# Helper Functions
# =============================================================================

def _convert_planner_input_to_response(
    planner_input: dict
) -> PlannerInputResponse:
    """Planner 입력을 API 응답 형식으로 변환"""
    
    channel_profile = ChannelProfileResponse(
        **planner_input["channel_profile"]
    )
    
    topic_context = None
    if planner_input.get("topic_context"):
        topic_context = TopicContextResponse(
            **planner_input["topic_context"]
        )
    
    return PlannerInputResponse(
        topic=planner_input["topic"],
        channel_profile=channel_profile,
        topic_context=topic_context,
    )
