
# Script Gen 에이전트 상세 현황 보고서

## 1. 개요
사용자가 제공한 이상적인 워크플로우(Planner -> Research -> Analyzer -> Insight -> Writer)와 실제 파일 상태를 대조한 결과입니다.

**결론적으로:** 
- **Planner (기획)** 와 **News Researcher (뉴스 수집)** 는 완성되어 있습니다.
- **나머지 연결 고리들(YouTube 수집, 경쟁사 분석, 인사이트 도출, 대본 작성)** 은 파일만 있고 내용은 **텅 비어 있습니다.**

---

## 2. 모듈별 상세 상태 (O / X 판정)

| 순서 | 에이전트 / 역할 | 파일 위치 (`src/script_gen/nodes/`) | 상태 | 상세 내용 |
|:---:|:---|:---|:---:|:---|
| 1 | **Planner** <br>(기획) | `planner.py` | **O** | **[완벽 구현]**<br>- 주제를 받아 5단 챕터 구성안 생성<br>- 재시도 로직 및 JSON 검증 포함<br>- Tavily 검색으로 최신 정보 반영 |
| 2-A | **Researcher** <br>(뉴스 조사) | `news_research.py` | **O** | **[완벽 구현]**<br>- 뉴스 딥서치, 중복 제거, 이미지 크롤링<br>- 팩트 추출(`_structure_facts`) 기능 통합됨 |
| 2-B | **YouTube Fetcher** <br>(영상 수집) | `yt_fetcher.py` | **X** | **[비어있음 - 0 byte]**<br>- `app/services/youtube_service.py`에 API 기능은 있으나, 에이전트용 노드 로직이 없음 |
| 3 | **Competitor Analyzer** <br>(경쟁사 분석) | `competitor_anal.py` | **X** | **[비어있음 - 0 byte]**<br>- 수집된 경쟁사 영상을 분석하는 로직 부재 |
| 4 | **Insight Builder** <br>(차별화 포인트) | `insight_builder.py` | **X** | **[비어있음 - 0 byte]**<br>- "내 영상만의 포인트"를 만드는 핵심 두뇌 부재 |
| 5 | **Writer** <br>(대본 작성) | `writer.py` | **X** | **[비어있음 - 0 byte]**<br>- 조사된 자료를 바탕으로 실제 글을 쓰는 작가 부재 |
| 6 | **Verifier** <br>(검증) | `verifier.py` | **X** | **[비어있음 - 0 byte]**<br>- 팩트 체크 및 출처 정리 로직 부재 |

---

## 3. 긴급 조치 제언 (Action Plan)

워크플로우가 끊기지 않고 돌아가게 하려면 **반드시** 채워야 할 '최소 기능' 순서입니다.

1.  **YouTube Fetcher (`yt_fetcher.py`) 작성**:
    - `planner.py`가 만든 검색어(`competitorQuery`)를 받아서 `YouTubeService`를 호출해 실제 영상 데이터를 가져오는 다리 역할을 만들어야 합니다.

2.  **Insight Builder (`insight_builder.py`) 작성**:
    - 뉴스와 유튜브 자료를 섞어서 "그래서 우린 뭘 다르게 할 건데?"라는 결론(한 줄 핵심 주장)을 내리는 로직이 필요합니다. 이게 없으면 대본이 밋밋해집니다.

3.  **Writer (`writer.py`) 작성**:
    - 가장 중요합니다. 위에서 모은 모든 재료(기획안 + 뉴스 + 영상 분석 + 인사이트)를 버무려 실제 대본 텍스트를 생성해야 합니다.

4.  **Orchestrator (`graph.py`) 작성**:
    - 이 모든 노드들을 순서대로 연결해 주는 배선 작업이 필요합니다.
