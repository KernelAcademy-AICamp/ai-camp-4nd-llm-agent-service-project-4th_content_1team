"""
뉴스 리서치 에이전트 테스트 스크립트
키워드: 부동산 가격 상승률
"""
import sys
import os
import logging

# 로깅 설정 (DEBUG 레벨로 상세 로그 출력)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

# .env 파일 로드
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(__file__))

from src.script_gen.nodes.news_research import news_research_node
import json

# 테스트 입력 데이터
test_state = {
    "content_brief": {
        "researchPlan": {
            "newsQuery": ["부동산 가격 상승률"],
            "competitorQuery": [],
            "freshnessDays": 30
        }
    }
}

print("=" * 60)
print("뉴스 리서치 에이전트 테스트 시작")
print("키워드:2026 프로야구 연봉")
print("=" * 60)
print()

# 뉴스 수집 실행
result = news_research_node(test_state)

# 결과 출력
news_data = result.get("news_data", {})
articles = news_data.get("articles", [])

print(f"✅ 수집된 기사 수: {len(articles)}개")
print()

for idx, article in enumerate(articles, 1):
    print(f"[기사 {idx}]")
    print(f"제목: {article.get('title', 'N/A')}")
    print(f"URL: {article.get('url', 'N/A')}")
    print(f"본문 길이: {len(article.get('content', ''))}자")
    print(f"이미지 수: {len(article.get('images', []))}개")
    print(f"차트 수: {len(article.get('charts', []))}개")
    print(f"표 수: {len(article.get('tables', []))}개")
    
    # 이미지 상세 정보
    if article.get('images'):
        print("  이미지:")
        for img_idx, img in enumerate(article['images'][:3], 1):  # 최대 3개만 표시
            print(f"    {img_idx}. {img['width']}x{img['height']} - {img['url'][:80]}...")
    
    # 차트 상세 정보
    if article.get('charts'):
        print("  차트:")
        for chart_idx, chart in enumerate(article['charts'], 1):
            print(f"    {chart_idx}. {chart['width']}x{chart['height']} - {chart['url'][:80]}...")
    
    # 표 상세 정보
    if article.get('tables'):
        print("  표:")
        for table_idx, table in enumerate(article['tables'], 1):
            print(f"    {table_idx}. {table['path']}")
    
    print()
    print("-" * 60)
    print()

# JSON 파일로 저장
output_file = "test_news_result.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"📁 결과가 {output_file}에 저장되었습니다.")
