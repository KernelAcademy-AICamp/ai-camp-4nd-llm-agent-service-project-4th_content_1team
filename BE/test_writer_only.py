import json
import os
import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.script_gen.nodes.writer import writer_node

def test_writer_only():
    print("🚀 Writer Node 단독 테스트 시작...")
    
    # 1. 기존 뉴스 데이터 로드 (Articles)
    json_path = os.path.join(os.path.dirname(__file__), "test_news_result.json")
    if not os.path.exists(json_path):
        print(f"❌ 데이터 파일 없음: {json_path}")
        print("먼저 test_news_only.py를 실행하여 데이터를 생성해주세요.")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    # [FIX] 딕셔너리로 오면 리스트 추출 시도
    if isinstance(data, dict):
        if "articles" in data:
            articles = data["articles"]
        elif "news_data" in data and "articles" in data["news_data"]:
            articles = data["news_data"]["articles"]
        else:
            print("⚠️ JSON 구조가 예상과 다릅니다. (news_data > articles 키 없음)")
            articles = []
    else:
        articles = data
        
    print(f"✅ 기사 데이터 로드 완료: {len(articles)}개")
    
    # [DEBUG] 데이터 타입 확인
    if len(articles) > 0:
        print(f"🔍 첫 번째 아이템 타입: {type(articles[0])}")
        print(f"🔍 내용 미리보기: {str(articles[0])[:100]}...")

    # 2. 데이터 가공 (News Research Node가 하는 일을 흉내냄)
    structured_facts = []
    structured_opinions = []
    
    for art in articles:
        # Facts 추출 (단순 flatten)
        facts = art.get("analysis", {}).get("facts", [])
        for f in facts:
            structured_facts.append({
                "id": f"fact-{len(structured_facts)}",
                "category": "extracted",
                "content": f,
                "source_indices": []
            })
            
        # Opinions 추출
        ops = art.get("analysis", {}).get("opinions", [])
        source = art.get("source", "Unknown")
        for op in ops:
            structured_opinions.append(f"[{source}] {op}")

    print(f"📊 Facts: {len(structured_facts)}개, Opinions: {len(structured_opinions)}개 준비됨")

    # 3. Mock Insight Blueprint (Insight Builder 결과 흉내)
    mock_insight_pack = {
        "positioning": {
            "thesis": "2026년은 대한민국 부동산과 경제의 거대한 변곡점이 될 것이다.",
            "one_sentence_promise": "이 영상을 통해 2026년 격변하는 시장의 흐름을 미리 읽고 대비할 수 있습니다."
        },
        "hook_plan": {
            "hook_type": "Curiosity Gap",
            "hook_scripts": [
                {"text": "여러분, 혹시 2026년이 한국 경제에 어떤 의미인지 알고 계신가요?"},
                {"text": "단순한 미래가 아닙니다. 전문가들은 '생존의 갈림길'이라고 경고하고 있습니다."}
            ],
            "uses_fact_ids": [structured_facts[0]["id"]] if structured_facts else []
        },
        "story_structure": {
            "chapters": [
                {
                    "title": "트렌드 1: 경제 및 산업 지표의 변화",
                    "goal": "거시 경제 지표와 산업별 통계 변화를 상세히 설명",
                    "key_points": ["유로화 도입", "GDP 성장률", "물가 상승", "산업별 수출입"],
                    "required_facts": [f["id"] for f in structured_facts[:6]] if len(structured_facts) >= 6 else []
                },
                {
                    "title": "트렌드 2: 부동산 및 시장 격변",
                    "goal": "부동산 거래량과 가격 변동성, 시장 반응 분석",
                    "key_points": ["상업용 부동산", "거래 규모", "투자 수익률", "지역별 차이"],
                    "required_facts": [f["id"] for f in structured_facts[6:12]] if len(structured_facts) >= 12 else []
                },
                {
                    "title": "트렌드 3: 전문가들의 경고와 미래 전략",
                    "goal": "전문가들의 시각을 통해 위기와 기회를 동시에 조명하고 행동 지침 제시",
                    "key_points": ["전문가 전망", "업계 반응", "투자 전략", "리스크 관리"],
                    "required_facts": [f["id"] for f in structured_facts[12:]] if len(structured_facts) > 12 else []
                }
            ]
        },
        "writer_instructions": {
            "reading_level": "Intermediate",
            "tone": "Analyze, Professional but Accessible"
        }
    }

    # 4. Mock Channel Profile
    mock_channel = {
        "name": "돈이 보이는 경제",
        "target_audience": "20~40대 재테크 관심층",
        "tone": "객관적이고 신뢰감 있는"
    }

    # 5. State 구성
    state = {
        "topic_request_id": "test-req-123",
        "channel_profile": mock_channel,
        "insight_pack": mock_insight_pack,
        "news_data": {
            "articles": articles,
            "structured_facts": structured_facts,
            "structured_opinions": structured_opinions
        }
    }

    # 6. Writer Node 실행
    print("\n📝 Writer Node 실행 중... (대본 작성)")
    result = writer_node(state)
    
    # 7. 결과 출력
    draft = result["script_draft"]["script"]
    
    # 7. 결과 저장 (가장 먼저 수행)
    output_path = os.path.join(os.path.dirname(__file__), "test_script_result.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\n✅ 대본 결과 저장 완료: {output_path}")

    # 8. 결과 출력 (오류나도 저장된 파일은 남도록)
    print("\n" + "="*50)
    print("🎬 생성된 대본 (Script Result)")
    print("="*50)
    
    # [DEBUG] 구조 확인용
    print(f"DEBUG: Draft Keys: {draft.keys()}")
    if 'hook' in draft:
        print(f"DEBUG: Hook Keys: {draft['hook'].keys()}")

    try:
        # [FIX] 키 이름 'script' -> 'text'로 수정
        print(f"\n[HOOK]\n{draft['hook']['text']}") 
        print(f"(References: {draft['hook'].get('fact_references', [])})")
        
        for i, ch in enumerate(draft['chapters'], 1):
            print(f"\n[Chapter {i}] {ch['title']}")
            for beat in ch['beats']:
                print(f"- {beat['line']}")
                if beat.get('fact_references'):
                    print(f"  └─ 🔗 {beat['fact_references']}")
        
        print(f"\n[OUTRO]\n{draft['closing']['text']}")
        
        # 길이 분석
        full_text = draft['hook']['text']
        for ch in draft['chapters']:
            for beat in ch['beats']:
                full_text += " " + beat['line']
        full_text += " " + draft['closing']['text']
        
        word_count = len(full_text.split())
        char_count = len(full_text)
        
        print("\n" + "="*50)
        print(f"📏 길이 분석: 공백포함 {char_count}자 / 단어 {word_count}개")
        print("="*50)
    except Exception as e:
        print(f"\n⚠️ 출력 중 에러 발생: {e}")
        print(">> 생성된 test_script_result.json 파일을 직접 확인하세요.")

if __name__ == "__main__":
    test_writer_only()
