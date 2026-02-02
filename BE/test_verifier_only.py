import sys
import os
import json
import logging

# 프로젝트 루트 경로 추가 (모듈 import를 위해)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.script_gen.nodes.verifier import verifier_node

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def test_verifier_only():
    print("=" * 60)
    print("🕵️  Verifier Node 단독 테스트 (검증 절차)")
    print("=" * 60)

    # 1. 파일 경로 설정
    base_dir = os.path.dirname(__file__)
    script_path = os.path.join(base_dir, "test_script_result.json")
    news_path = os.path.join(base_dir, "test_news_result.json")

    # 2. 파일 존재 확인
    if not os.path.exists(script_path):
        print(f"❌ 대본 파일이 없습니다: {script_path}")
        print(">> 먼저 test_writer_only.py를 실행하여 대본을 생성하세요.")
        return
    
    if not os.path.exists(news_path):
        print(f"❌ 뉴스 데이터 파일이 없습니다: {news_path}")
        print(">> 먼저 test_news_only.py를 실행하여 데이터를 생성하세요.")
        return

    # 3. 데이터 로드
    print("📂 데이터 로드 중...")
    
    # (1) Script Draft 로드
    with open(script_path, "r", encoding="utf-8") as f:
        script_data = json.load(f)
        # script_draft 키 아래에 있는지, 아니면 바로 객체인지 확인
        if "script_draft" in script_data:
            script_draft = script_data["script_draft"]
        else:
            script_draft = script_data

    # (2) News Data 로드 및 Fact ID 재구성
    # Writer 테스트 때와 동일한 방식으로 Fact ID를 만들어야 매칭이 됩니다.
    with open(news_path, "r", encoding="utf-8") as f:
        raw_news = json.load(f)

    # 뉴스 데이터 정규화
    if isinstance(raw_news, dict):
        if "articles" in raw_news:
            articles = raw_news["articles"]
        elif "news_data" in raw_news and "articles" in raw_news["news_data"]:
            articles = raw_news["news_data"]["articles"]
        else:
            articles = []
    else:
        articles = raw_news

    # Fact ID 재생성 (Writer Test와 동일 로직)
    structured_facts = []
    for art in articles:
        facts = art.get("analysis", {}).get("facts", [])
        for f in facts:
            structured_facts.append({
                "id": f"fact-{len(structured_facts)}",  # fact-0, fact-1, ...
                "category": "extracted",
                "content": f,
                "article_id": art.get("id", "unknown"), # 출처 추적용
                "source_indices": []
            })
    
    print(f"✅ 대본 로드 완료: {script_draft.get('metadata', {}).get('title', 'Untitled')}")
    print(f"✅ 뉴스 팩트 준비 완료: {len(structured_facts)}개 (fact-0 ~ fact-{len(structured_facts)-1})")

    # 4. State 구성 (Verifier Node에 들어갈 입력)
    state = {
        "script_draft": script_draft,
        "news_data": {
            "articles": articles,
            "structured_facts": structured_facts
        }
    }

    # 5. Verifier Node 실행
    print("\n🔍 검증 시작... (Verifier Node Running)")
    try:
        result_state = verifier_node(state)
        output = result_state["verifier_output"]
    except Exception as e:
        print(f"\n❌ 실행 중 에러 발생: {e}")
        logger.error("Verifier Error", exc_info=True)
        return

    # 6. 결과 분석 및 출력
    print("\n" + "=" * 60)
    print("📊 [검증 결과 리포트]")
    print("=" * 60)
    
    report = output["verification_report"]
    print(f"✅ 검증 통과 여부: {'PASS' if output['verified'] else 'WARNING'}")
    print(f"📉 검증된 Beats: {report['verified_beats']} / {report['total_beats']}")
    print(f"🔗 유효한 Fact 참조: {report['valid_fact_references']} / {report['total_fact_references']}")
    
    if report["issues"]:
        print(f"\n⚠️ 발견된 이슈 ({len(report['issues'])}개):")
        for issue in report["issues"]:
            print(f"  - [{issue['severity'].upper()}] {issue['description']} (Beat: {issue['beat_id']})")
    else:
        print("\n✨ 발견된 이슈 없음 (Clean!)")

    # 7. Source Map (출처 연결) 확인
    source_map = output["source_map"]
    print(f"\n📚 출처 연결 확인 ({len(source_map)}개 문장):")
    for i, entry in enumerate(source_map[:3]): # 상위 3개만 출력
        print(f"\n  #{i+1} 문장: \"{entry['sentence']}...\"")
        for source in entry['sources']:
            print(f"     → 출처: [{source['publisher']}] {source['url']}")

    # 8. 최종 결과 저장
    output_path = os.path.join(base_dir, "test_final_result.json")
    
    # 기존 대본에 검증 결과 합치기
    final_result = script_draft.copy()
    final_result["verifier_output"] = output
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_result, f, indent=2, ensure_ascii=False)
        
    print("\n" + "=" * 60)
    print(f"💾 최종 결과(대본+검증) 저장 완료: {output_path}")
    print("=" * 60)

if __name__ == "__main__":
    test_verifier_only()
