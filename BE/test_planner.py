import os
import sys
import json
from dotenv import load_dotenv

# 현재 디렉토리(BE)를 path에 추가하여 src 모듈을 찾을 수 있게 함
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# src 아래의 모듈 임포트
try:
    from src.script_gen.nodes.planner import planner_node
except ImportError as e:
    print(f"Import Error: {e}")
    print("PYTHONPATH를 확인하거나 BE 폴더에서 스크립트를 실행해주세요.")
    sys.exit(1)

def test_planner():
    # 1. 환경변수 로드 (.env 파일이 BE 폴더에 있어야 함)
    load_dotenv()
    
    # API 키 확인
    if not os.getenv("GOOGLE_API_KEY"):
        print("경고: GOOGLE_API_KEY가 .env에 설정되지 않았습니다.")
    if not os.getenv("TAVILY_API_KEY"):
        print("경고: TAVILY_API_KEY가 .env에 설정되지 않았습니다. (뉴스 검색 실패 가능)")

    # 2. 테스트용 입력 데이터 (State)
    # 실제 사용자가 입력할 법한 주제와 채널 프로필을 모의로 작성
    test_state = {
        "topic": "AGI(일반 인공지능)가 5년 안에 올까?",
        "channel_profile": {
            "name": "미래 기술 연구소",
            "category": "Tech & Future",
            "target_audience": "IT 기술 변화에 민감한 2040 직장인 및 학생",
            "average_duration": 12,  # 12분 영상 목표
            "content_style": "전문적인 분석과 쉬운 비유를 섞은 설명형",
            "recent_feedback": [
                "너무 어려운 전문 용어는 자막으로 설명해주세요",
                "긍정적인 면과 부정적인 면을 균형 있게 다뤄주세요"
            ]
        }
    }
    
    print("\n" + "="*50)
    print("🎬 Planner Node 테스트 시작")
    print("="*50)
    print(f"📌 주제: {test_state['topic']}")
    print(f"📌 채널: {test_state['channel_profile']['name']}")
    print("-" * 50)
    print("⏳ 기획안 생성 중... (뉴스 검색 및 LLM 생성)")

    try:
        # 3. 노드 실행
        # planner_node는 내부적으로 재시도 로직이 있어서 시간이 조금 걸릴 수 있음
        result = planner_node(test_state)
        
        # 4. 결과 출력
        content_brief = result.get("content_brief")
        
        print("\n" + "="*50)
        print("✅ 기획안 생성 완료 (Content Brief)")
        print("="*50)
        
        # 보기 좋게 JSON 출력
        print(json.dumps(content_brief, indent=2, ensure_ascii=False))
        
        print("\n" + "="*50)
        print("Key Elements 확인:")
        print(f"- 챕터 수: {len(content_brief['narrative']['chapters'])}개 (목표: 5개)")
        print(f"- 뉴스 검색어: {len(content_brief['researchPlan']['newsQuery'])}개")
        print(f"- 제목 후보: {len(content_brief['workingTitleCandidates'])}개")
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_planner()
