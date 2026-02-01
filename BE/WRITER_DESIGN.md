# Writer Agent Design Doc

## 1. 개요 (Overview)
Writer 에이전트는 기획된 '대본 설계도(Blueprint)'와 수집된 '팩트(FactPack)'를 바탕으로 **유튜브용 스크립트(Script)**를 작성하는 최종 집필자입니다.
단순히 정보를 나열하는 것이 아니라, **페르소나**에 빙의하여 **스토리텔링**을 수행하고, 편집자가 바로 작업할 수 있도록 **시각/청각 요소(Audio/Visual)**를 분리하여 출력합니다.

## 2. 입력 데이터 구조 (Input Packs)

Writer는 다음 3가지 핵심 데이터를 입력으로 받습니다. (Data Flow Diagram 준수)

### A. Blueprint (대본 설계도 - From Insight Builder)
> Insight Builder가 전략적으로 짜놓은 뼈대
- **Thesis (핵심 주장)**: 영상 전체를 관통하는 하나의 메시지 (예: "트럼프의 골룸 비유는 단순 실수가 아니라 고도의 전략이다.")
- **POV (차별화 포인트)**: 남들과 다른 시각 2~4개
- **Hooks**: 초반 15초를 사로잡을 강렬한 멘트 2개
- **Structure**: 5챕터 구성안 (각 챕터의 목표와 필수 포함 팩트 지정)

### B. FactPack (팩트 꾸러미 - From News Research)
> News Research가 발굴하고 구조화한 재료
- **Structured Facts**: 수치, 통계, 전문가 발언 (JSON 형태)
- **Visual Proposals**: "이 숫자는 차트로 그려라", "이 발언은 인용 카드로 띄워라" 제안
- **Article Summaries**: 기사 원문 문단 (문맥 파악용)

### C. CompetitorPack (경쟁사 꾸러미 - From Competitor Analyzer)
> (Optional) 경쟁 영상 분석 데이터
- **Reference Expressions**: 경쟁 영상에서 좋았던 표현/구조 (참고용)
- **Validation**: "경쟁사는 이렇게 말했으니 우리는 다르게 말하자"는 가이드

## 3. 작동 로직 (Workflow)

Writer는 토큰 제한(Context Limit)과 퀄리티 유지를 위해 **"챕터별 연쇄 생성(Chain-of-Generation)"** 방식을 사용합니다.

### Phase 1. Persona Loading (페르소나 로딩)
- 사용자가 설정한 채널의 페르소나(톤앤매너)를 시스템 프롬프트에 주입합니다.
- 예: "냉소적인 IT 전문가", "텐션 높은 동네 형"

### Phase 2. Chapter-by-Chapter Writing (챕터별 집필)
한 번에 통으로 쓰지 않고, 챕터 1부터 5까지 순차적으로 생성합니다.

1.  **Chapter 1 (Intro/Hook)**:
    - Insight Builder가 준 `Hooks`를 활용하여 시선을 끔.
    - `Thesis`(핵심 주장)를 암시.
2.  **Chapter 2~4 (Body)**:
    - 각 챕터에 할당된 `Structured Facts`를 문장에 자연스럽게 녹임.
    - **중요**: 팩트를 말할 때는 반드시 `[Visual Proposal]`을 활용하여 화면 연출 지시.
3.  **Chapter 5 (Outro/Action)**:
    - `Thesis`를 다시 한번 강조하며 마무리.
    - 구독/좋아요 유도 (Call to Action).

### Phase 3. Context Maintenance (문맥 유지)
- 이전 챕터 내용을 다음 챕터 생성 시 `Context`로 넘겨주어, 말이 끊기지 않고 이어지게 함. ("앞서 말씀드린 것처럼~")

## 4. 출력 데이터 포맷 (Output Schema)

최종 산출물은 편집자가 보기 편한 **Markdown** 또는 **JSON** 형식입니다.

```markdown
# [SCRIPT] 랜드 폴의 골룸 발언, 그 속뜻은?

## 🎬 Chapter 1: 오프닝
**(Visual: 랜드 폴이 소리치는 사진 + '골룸?' 자막)**
**(Audio)**: 여러분, 미국 상원의원이 전직 대통령보고 '골룸'이라니... 이게 말이 됩니까? 정치판이 완전 반지의 제왕이 됐습니다.

## 🎬 Chapter 2: 사건의 전말
**(Visual: 트럼프와 골룸 비교 사진)**
**(Audio)**: 그런데 이 사진을 한번 보세요. (웃음) 솔직히 좀 닮은 것 같기도 하죠? 하지만 랜드 폴 의원이 단순히 웃기려고 이런 말을 했을까요? 천만의 말씀입니다.

**(Visual: 막대 그래프 - 랜드 폴 지지율 변화)**
**(Audio)**: 팩트를 봅시다. 이 발언 직후 랜드 폴의 검색량이 무려 500% 폭증했습니다. 이건 철저히 계산된 어그로라는 거죠.
```

## 5. 핵심 기능 (Key Features)

1.  **Fact-Checking Enforcement**: 없는 말을 지어내지 못하게, 문장 끝에 `(Source: Article #1)` 처럼 주석을 달게 할 수 있음.
2.  **Visual Directing**: 대본만 쓰는 게 아니라, **"여기서 무슨 화면을 보여줄지"** 지시문을 반드시 포함해야 함.
3.  **Tone Consistency**: 처음부터 끝까지 페르소나의 말투(비속어 허용 여부, 존대/반말 등)를 유지.

## 6. 개발 로드맵
1.  `writer.py` 노드 생성
2.  `Persona` 프롬프트 템플릿 설계
3.  `Chapter Generator` 함수 구현 (LangChain)
4.  통합 테스트 연결
