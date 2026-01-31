"""
초기 썸네일 전략 데이터 마이그레이션

기본 5가지 썸네일 전략을 DB에 저장합니다.
"""
import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import AsyncSessionLocal
from app.services.agents.strategy_scraper import StrategyScraper


# 기본 전략 5가지
DEFAULT_STRATEGIES = [
    {
        "id": "curiosity_gap",
        "name_kr": "호기심 자극형",
        "content": """호기심 자극형 (Curiosity Gap) 전략은 정보의 일부만 공개하여 시청자의 궁금증을 유발하는 방식입니다.

**핵심 원리:**
- 질문 형식으로 제목 구성 ("이것만 알면?", "놀라운 비밀은?")
- 결과만 언급하고 과정은 숨김 ("이렇게 했더니 대박")
- 반전/놀라움 암시 ("예상 못한 결과", "충격적인 사실")

**비주얼 전략:**
- 신비로운 분위기 (어두운 배경, 하이라이트)
- 물음표, 느낌표 등 강조 요소
- 모호한 이미지 (전체를 보여주지 않음)

**효과:**
클릭률(CTR) 증가에 가장 효과적. 정보성 콘텐츠에 적합.""",
        "source_url": "https://blog.hubspot.com/marketing/curiosity-gap"
    },
    {
        "id": "loss_aversion",
        "name_kr": "손실 회피형",
        "content": """손실 회피형 (Loss Aversion) 전략은 '놓치면 손해'라는 심리를 자극합니다.

**핵심 원리:**
- 부정 표현 사용 ("모르면 손해", "하지 않으면 후회")
- 위험/경고 암시 ("치명적인 실수", "위험한 습관")
- 시간 제한 강조 ("지금 바로", "마감 임박")

**비주얼 전략:**
- 경고색 사용 (빨강, 주황)
- 금지/주의 아이콘
- 대비가 강한 색상 배치

**효과:**
즉각적인 행동 유도에 효과적. 교육/경고성 콘텐츠에 적합.""",
        "source_url": "https://www.nngroup.com/articles/prospect-theory/"
    },
    {
        "id": "authority",
        "name_kr": "권위형",
        "content": """권위형 (Authority) 전략은 전문성과 신뢰를 강조합니다.

**핵심 원리:**
- 전문가/기관 인용 ("전문가가 말하는", "연구 결과")
- 통계/수치 제시 ("98% 효과", "10년 경력")
- 공식/검증 강조 ("공식 발표", "인증된 방법")

**비주얼 전략:**
- 전문적인 디자인 (깔끔, 정돈)
- 차트/그래프 요소
- 인증 마크, 로고 배치
- 전문가 이미지 (정장, 사무실)

**효과:**
신뢰도 향상. 전문 지식/정보 콘텐츠에 적합.""",
        "source_url": "https://www.influenceatwork.com/principles-of-persuasion/"
    },
    {
        "id": "social_proof",
        "name_kr": "사회적 증거형",
        "content": """사회적 증거형 (Social Proof) 전략은 다수의 선택/인기를 강조합니다.

**핵심 원리:**
- 인기/트렌드 강조 ("요즘 핫한", "다들 하는")
- 숫자 제시 ("조회수 100만", "구독자 급증")
- 후기/추천 언급 ("극찬", "화제")

**비주얼 전략:**
- 군중/사람 이미지
- 통계 그래프 (상승 화살표)
- 별점/좋아요 아이콘
- 밝고 긍정적인 색상

**효과:**
신뢰 구축 및 유행 따라가기 심리 자극. 트렌드/리뷰 콘텐츠에 적합.""",
        "source_url": "https://www.influenceatwork.com/principles-of-persuasion/"
    },
    {
        "id": "scarcity",
        "name_kr": "희소성형",
        "content": """희소성형 (Scarcity) 전략은 '한정/희귀' 가치를 강조합니다.

**핵심 원리:**
- 수량/시간 제한 ("마지막 기회", "단 3일")
- 독점/특별 강조 ("이것만", "오직 여기서만")
- 경쟁 암시 ("빨리 마감", "선착순")

**비주얼 전략:**
- 타이머/시계 이미지
- 제한 표시 (LIMITED, EXCLUSIVE)
- 강렬한 색상 (골드, 레드)
- 숫자 카운트다운 효과

**효과:**
즉각 행동 유도. 이벤트/프로모션 콘텐츠에 적합.""",
        "source_url": "https://www.influenceatwork.com/principles-of-persuasion/"
    }
]


async def migrate_strategies():
    """
    기본 전략을 DB에 마이그레이션
    
    Returns:
        int: 저장된 전략 개수
    """
    async with AsyncSessionLocal() as session:
        scraper = StrategyScraper()
        count = await scraper.run(session, strategies=DEFAULT_STRATEGIES)
        print(f"✅ Successfully migrated {count} strategies")
        return count


async def verify_migration():
    """마이그레이션 결과 확인"""
    from app.services.strategy_loader import StrategyLoader
    
    async with AsyncSessionLocal() as session:
        loader = StrategyLoader()
        strategies = await loader.get_all_strategies(session)
        
        print(f"\n📊 Total strategies in DB: {len(strategies)}")
        print("\n전략 목록:")
        for strategy in strategies:
            print(f"  - {strategy.id}: {strategy.name_kr}")
        
        return strategies


async def main():
    """메인 실행 함수"""
    print("🚀 Starting thumbnail strategy migration...")
    print(f"📦 Migrating {len(DEFAULT_STRATEGIES)} default strategies\n")
    
    try:
        # 마이그레이션 실행
        count = await migrate_strategies()
        
        # 결과 확인
        await verify_migration()
        
        print("\n✅ Migration completed successfully!")
        return 0
    
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
