"""
Script Generation Pipeline 통합 테스트

전체 워크플로우를 실행하여 주제 → 대본 생성이 정상 작동하는지 검증합니다.
"""

import sys
import os
import logging

# 프로젝트 루트를 Python Path에 추가
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.script_gen.graph import generate_script
import json

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def save_json(step_name, data):
    """중간 결과 저장 헬퍼"""
    filename = f"result_{step_name}.json"
    try:
        # Pydantic 모델인 경우 dict로 변환
        if hasattr(data, 'model_dump'):
            data = data.model_dump()
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"   💾 [{step_name}] 저장 완료: {filename}")
    except Exception as e:
        print(f"   ⚠️ [{step_name}] 저장 실패: {e}")

def test_full_pipeline():
    """전체 파이프라인 테스트 (단계별 저장 포함)"""
    
    print("=" * 80)
    print("🚀 Script Generation Pipeline 통합 테스트 (Step-by-Step Logging)")
    print("=" * 80)
    
    # 테스트 입력
    topic = "2024년 AI 반도체 시장의 최신 동향과 전망"
    channel_profile = {
        "name": "테크 인사이트 TV",
        "tone": "분석적이지만 쉬운 설명",
        "target_audience": "IT 관심 일반인 및 투자자",
        "category": "Technology",
        "avg_video_length_min": 10
    }
    
    print(f"\n📌 주제: {topic}")
    
    # [Direct Node Execution to capture intermediate states]
    # graph.py의 CompiledGraph를 쓰면 중간 상태를 보기 힘드므로
    # 여기서는 노드 함수를 직접 순차 실행하여 결과를 저장합니다.
    
    from src.script_gen.nodes.trend_scout import trend_scout_node
    from src.script_gen.nodes.planner import planner_node
    from src.script_gen.nodes.news_research import news_research_node
    from src.script_gen.nodes.yt_fetcher import yt_fetcher_node
    from src.script_gen.nodes.competitor_anal import competitor_anal_node
    from src.script_gen.nodes.insight_builder import insight_builder_node
    from src.script_gen.nodes.writer import writer_node
    from src.script_gen.nodes.verifier import verifier_node
    
    # 초기 State
    state = {
        "topic": topic,
        "topic_request_id": "test_req_001",  # 필수 필드 추가
        "channel_profile": channel_profile
    }
    
    try:
        # [Smart Resume Logic]
        # Step 6(InsightPack)와 Step 3(NewsData)가 있다면 로드하고 바로 Writer로 점프
        should_skip_to_writer = False
        if os.path.exists("result_06_InsightPack.json") and os.path.exists("result_03_NewsResearch.json"):
            print("\n⏩ [RESUME] 기존 파일 발견! Insight Builder 단계까지 건너뛰고 Writer부터 시작합니다.")
            try:
                with open("result_03_NewsResearch.json", "r", encoding="utf-8") as f:
                    state.update(json.load(f))
                with open("result_06_InsightPack.json", "r", encoding="utf-8") as f:
                    state.update(json.load(f))
                should_skip_to_writer = True
            except Exception as e:
                print(f"⚠️ 파일 로드 실패, 처음부터 시작합니다: {e}")

        if not should_skip_to_writer:
            # 1. Trend Scout
            print("\n🔹 [Step 1] Trend Scout 실행 중...")
            res_1 = trend_scout_node(state)
            state.update(res_1)
            save_json("01_TrendScout", res_1)
            
            # 2. Planner
            print("\n🔹 [Step 2] Planner 실행 중...")
            res_2 = planner_node(state)
            state.update(res_2)
            save_json("02_Planner", res_2)
            
            # 3. News Research & YT Fetcher (Sequential for Test)
            print("\n🔹 [Step 3] News Research 실행 중...")
            res_3 = news_research_node(state)
            state.update(res_3)
            save_json("03_NewsResearch", res_3)
            
            print("\n🔹 [Step 4] YT Fetcher 실행 중...")
            res_4 = yt_fetcher_node(state)
            state.update(res_4)
            save_json("04_YTFetcher", res_4)
            
            # 4. Competitor Analyzer
            print("\n🔹 [Step 5] Competitor Analyzer 실행 중...")
            res_5 = competitor_anal_node(state)
            state.update(res_5)
            save_json("05_Competitor", res_5)
            
            # 5. Insight Builder
            print("\n🔹 [Step 6] Insight Builder 실행 중...")
            res_6 = insight_builder_node(state)
            state.update(res_6)
            save_json("06_InsightPack", res_6)
        
        # 6. Writer
        print("\n🔹 [Step 7] Writer 실행 중...")
        res_7 = writer_node(state)
        state.update(res_7)
        save_json("07_ScriptDraft", res_7)
        
        # 7. Verifier
        print("\n🔹 [Step 8] Verifier 실행 중...")
        res_8 = verifier_node(state)
        state.update(res_8)
        save_json("08_VerifierOutput", res_8)
        
        # [Manual Result Construction]
        # graph.py의 출력 형태와 유사하게 수동으로 구성
        result = {
            "topic": topic,
            "script_draft_id": state.get("script_draft", {}).get("script_draft_id"),
            "generated_at": state.get("script_draft", {}).get("generated_at"),
            "metadata": state.get("script_draft", {}).get("metadata", {}),
            "script": state.get("script_draft", {}).get("script", {}),
            "news_data": state.get("news_data", {}),
            "verifier_output": state.get("verifier_output", {})
        }

        print("\n" + "=" * 80)
        print("✅ 전체 파이프라인 완주 성공!")
        print("📂 현재 폴더에 생성된 'result_*.json' 파일들을 확인하세요.")
        print("=" * 80)
        
        # 상세 결과 출력 (화면용)
        script = result.get('script', {})
        hook = script.get('hook', {})
        chapters = script.get('chapters', [])
        
        print("\n� [상세 대본 내용]")
        print("-" * 40)
        
        # 1. Hook
        print(f"\n[Hook]")
        # Schema 변경 대응: visualDescription -> on_screen_cues / text -> text
        print(f"Text: {hook.get('text', 'N/A')[:50]}...")
        
        # 2. Body
        for ch in chapters:
            print(f"\n[Chapter {ch.get('chapter_id')}] {ch.get('title')}")
            for beat in ch.get('beats', []):
                print(f"  - ({beat.get('purpose')}): {beat.get('line', 'N/A')[:30]}...")

        print("\n" + "=" * 80)
        print("✨ 테스트 성공!")
        print("=" * 80)
        
        return result

    except Exception as e:
        print("\n❌ 테스트 중단 (Error Occurred)")
        print(f"Error: {e}")
        logger.error("Pipeline Flow Error", exc_info=True)
        raise


if __name__ == "__main__":
    test_full_pipeline()
