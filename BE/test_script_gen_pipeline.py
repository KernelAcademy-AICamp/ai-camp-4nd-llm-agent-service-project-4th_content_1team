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

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_full_pipeline():
    """전체 파이프라인 테스트"""
    
    print("=" * 80)
    print("🚀 Script Generation Pipeline 통합 테스트 시작")
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
    print(f"📌 채널: {channel_profile['name']}")
    print(f"📌 타겟: {channel_profile['target_audience']}\n")
    
    try:
        # 파이프라인 실행
        print("⏳ 파이프라인 실행 중... (Full Pipeline: 8 Nodes)")
        print("   0️⃣ Trend Scout: 레딧 트렌드 키워드 수집")
        print("   1️⃣ Planner: 목차 및 질문 생성")
        print("   2️⃣ News Research: 뉴스 수집 및 팩트 추출 (병렬)")
        print("   3️⃣ YT Fetcher: 유튜브 영상 검색 (병렬)")
        print("   4️⃣ Competitor Analyzer: 경쟁사 분석")
        print("   5️⃣ Insight Builder: 전략 수립 (2-Pass)")
        print("   6️⃣ Writer: 대본 작성")
        print("   7️⃣ Verifier: 팩트 체크 & 출처 정리\n")
        
        result = generate_script(topic, channel_profile)
        
        # 결과 출력
        print("\n" + "=" * 80)
        print("✅ 대본 생성 완료!")
        print("=" * 80)
        
        print(f"\n📄 Script ID: {result.get('script_draft_id')}")
        print(f"📅 생성 시각: {result.get('generated_at')}")
        
        metadata = result.get('metadata', {})
        print(f"\n📊 메타데이터:")
        print(f"   - 제목: {metadata.get('title')}")
        print(f"   - 훅 타입: {metadata.get('hookType')}")
        print(f"   - 예상 길이: {metadata.get('estimatedDurationMin')}분")
        print(f"   - 난이도: {metadata.get('readingLevel')}")
        
        script = result.get('script', {})
        hook = script.get('hook', {})
        chapters = script.get('chapters', [])
        
        print(f"\n🎬 Hook (처음 15초):")
        print(f"   {hook.get('text', 'N/A')[:200]}...")
        
        print(f"\n📚 챕터 구성 ({len(chapters)}개):")
        for i, ch in enumerate(chapters, 1):
            print(f"   {i}. {ch.get('title', 'Untitled')}")
            print(f"      - 비트 수: {len(ch.get('beats', []))}개")
        
        closing = script.get('closing', {})
        print(f"\n🎯 마무리 CTA:")
        print(f"   {closing.get('cta', 'N/A')}")
        
        # Quality Report
        quality = result.get('quality_report', {})
        print(f"\n📈 품질 리포트:")
        print(f"   - 사용된 Fact 수: {len(quality.get('used_fact_ids', []))}개")
        print(f"   - 미사용 필수 Fact: {len(quality.get('unused_required_fact_ids', []))}개")
        
        # Verification Report
        verifier_output = result.get('verifier_output', {})
        if verifier_output:
            ver_report = verifier_output.get('verification_report', {})
            print(f"\n✅ 검증 리포트:")
            print(f"   - 검증 통과 Beat: {ver_report.get('verified_beats', 0)}/{ver_report.get('total_beats', 0)}개")
            print(f"   - 유효 Fact 참조: {ver_report.get('valid_fact_references', 0)}/{ver_report.get('total_fact_references', 0)}개")
            print(f"   - 발견된 이슈: {len(ver_report.get('issues', []))}개")
            print(f"   - 의심스러운 Beat: {len(ver_report.get('suspicious_beats', []))}개")
            
            # 출처 맵 요약
            source_map = verifier_output.get('source_map', [])
            print(f"\n📚 출처 맵:")
            print(f"   - 춝 {len(source_map)}개 Beat에 출처 연결")
            if source_map:
                print(f"   - 예시: Beat '{source_map[0].get('beat_id')}' → {len(source_map[0].get('sources', []))}개 출처")
        
        print("\n" + "=" * 80)
        print("✨ 테스트 성공!")
        print("=" * 80)
        
        return result
        
    except Exception as e:
        print("\n" + "=" * 80)
        print("❌ 테스트 실패!")
        print("=" * 80)
        print(f"\n에러: {e}")
        logger.error("Pipeline 실행 실패", exc_info=True)
        raise


if __name__ == "__main__":
    test_full_pipeline()
