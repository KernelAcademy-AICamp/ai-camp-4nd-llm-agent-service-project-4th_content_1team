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
    ScriptGenExecuteResponse, # 추가된 스키마 임포트
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
from app.schemas.script_gen import (
    ScriptGenStartRequest,
    ScriptGenStartResponse,
    ScriptGenPlannerResponse,
    PlannerInputResponse,
    ChannelProfileResponse,
    TopicContextResponse,
    ScriptGenExecuteResponse,
    ScriptGenTaskResponse, # 추가된 스키마
)

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
        
        # 2. Celery Task 실행 (.delay() 사용)
        # 데이터는 직렬화 가능한 dict 형태여야 함
        task = task_generate_script.delay(
            topic=planner_input["topic"],
            channel_profile=planner_input["channel_profile"],
            topic_request_id=None
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
        
        # 2. 동기 파이프라인 실행 (스레드풀 사용)
        # generate_script는 동기 함수이므로 await run_in_threadpool 사용
        result_dict = await run_in_threadpool(
            generate_script,
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
