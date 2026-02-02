# Insight Builder 에이전트 설계서

## 1. 개요
Insight Builder는 단순한 정보 요약이 아니라, **"내 영상이 시청자에게 줄 수 있는 단 하나의 차별화된 가치(Thesis)"**를 정의하고, 이를 바탕으로 **Writer가 바로 대본을 쓸 수 있는 논리적인 설계도(Blueprint)**를 생성하는 핵심 전략 에이전트입니다.

## 2. 핵심 역할
1.  **Thesis(핵심 주장) 선정**: "이 주제에서 뻔하지 않은, 나만의 관점은 무엇인가?" 정의
2.  **Difference(차별화) 설계**: 경쟁 영상들의 갭, 오해, 반대 관점 등을 공략하여 유니크함 확보
3.  **Writer Brief(대본 설계도) 작성**: Writer가 문장력에만 집중할 수 있도록 훅, 구조, 근거, 시각 자료까지 완벽히 구조화

---

## 3. 입/출력 인터페이스

### Input (3-Pack)
1.  **Channel Brief**: 채널 페르소나, 타겟, 톤앤매너, 평균 지속 시간
2.  **Fact Pack** (from `FactExtractor`): 검증된 사실, 통계, 인용문, 시각화 제안, 경고(Warnings)
3.  **Competitor Pack** (from `CompetitorAnalyst`): 경쟁사 분석, 공통된 약점(Gaps), 댓글 반응(Needs)

### Output (JSON)
Writer에게 전달될 `InsightPack` 구조입니다.

```json
{
  "insightPackId": "ins_uuid",
  "positioning": {
    "thesis": "AI 반도체, 기술이 아니라 '전력 효율' 싸움이다.",
    "oneSentencePromise": "이 영상은 복잡한 AI 칩 기술을 '전력 비용' 관점에서 쉽게 풀어줍니다.",
    "whoIsThisFor": "AI 주식 투자자 및 테크 트렌드 팔로워",
    "whatTheyWillGet": "투자 관점에서 어떤 기업을 봐야 할지 명확한 기준"
  },
  "differentiators": [
    {
      "type": "counterargument",
      "title": "속도보다 전성비가 핵심",
      "description": "대부분 '성능'만 이야기할 때, 우리는 '운영 비용'을 이야기한다.",
      "whyUniqueVsCompetitors": "경쟁 영상 상위 3개 모두 벤치마크 점수만 비교함",
      "supporting": {
        "factIds": ["fact_12", "fact_05"],
        "competitorEvidence": [{"videoRefId": "vid_01", "gapSnippet": "전력 소모 언급 없음"}]
      }
    }
  ],
  "hookPlan": {
    "hookType": "controversy",
    "hookScripts": [
      { "id": "h1", "text": "엔비디아가 망한다면, 그건 성능 때문이 아닙니다. 바로 전기세 때문입니다.", "usesFactIds": ["fact_03"] }
    ],
    "thumbnailAngle": {
      "concept": "불타는 서버실 vs 차가운 서버실",
      "copyCandidates": ["AI의 숨겨진 비용", "전기세가 승자를 바꾼다"]
    }
  },
  "storyStructure": {
    "chapters": [
      {
        "chapterId": "c1",
        "title": "문제 제기: 성능의 함정",
        "goal": "시청자가 알고 있던 '성능 지상주의'가 틀렸음을 충격적으로 제시",
        "keyPoints": ["AI 모델이 커질수록 전기세가 기하급수적으로 증가함"],
        "requiredFacts": ["fact_03", "fact_09"],
        "visuals": [{"type": "chart", "ref": "chart_01", "caption": "연도별 데이터센터 전력 소모량 추이"}]
      }
    ]
  },
  "writerInstructions": {
    "tone": "Analyze but Easy (분석적이나 쉬운)",
    "readingLevel": "intermediate",
    "claimPolicy": {
      "noUnsourcedNumbers": true,
      "handleWarnings": "allow_in_body_with_context"
    }
  }
}
```

---

## 4. 내부 아키텍처 (2-Pass System)

이 에이전트는 **LangChain**을 사용하여 `생성(Pass 1)` -> `비평 및 수정(Pass 2)`의 2단계 구조로 동작합니다.

### Pass 1: Generate Blueprint (전략 수립)
*   **LLM Role**: Creative Strategist
*   **Goal**: 가능한 차별화 포인트(Thesis) 3가지를 도출하고, 그중 가장 강력하고 근거(Fact)가 확실한 하나를 선택하여 초안 생성.
*   **Prompt Key Point**:
    *   "경쟁 영상들이 다룬 내용은 '기본값'으로 간주하고, 그 위에 무엇을 더할지 고민하라."
    *   "Fact Pack에 없는 내용은 주장하지 마라."

### Pass 2: Critic & Repair (품질 감사)
*   **LLM Role**: Strict Editor
*   **Goal**: 1차 결과물의 논리적 오류, 진부함, 근거 부족을 찾아내어 수정하거나 반려.
*   **Checklist**:
    1.  **Originality Check**: 경쟁사 Top 영상과 전략이 겹치지 않는가?
    2.  **Evidence Check**: 핵심 주장(Thesis)을 뒷받침할 Fact ID가 매핑되어 있는가?
    3.  **Tone Check**: 채널 페르소나와 맞지 않는 너무 어렵거나 가벼운 표현은 없는가?

---

## 5. 구현 계획

1.  **Pydantic Models 정의**: 입/출력 JSON 스키마를 코드로 구현 (`src/script_gen/schemas/insight.py`)
2.  **Prompt Templates 작성**:
    *   `INSIGHT_GEN_PROMPT`: 팩트와 경쟁사 정보를 종합해 전략을 짜는 프롬프트
    *   `INSIGHT_CRITIC_PROMPT`: 전략의 타당성을 검증하는 프롬프트
3.  **LangGraph Node 구현**: `insight_builder_node` 함수 작성 (`src/script_gen/nodes/insight_builder.py`)
    *   Input State 파싱
    *   Pass 1 실행 (Chain)
    *   Pass 2 실행 (Chain)
    *   Output State 업데이트

---

## 6. Writer 에이전트와의 관계
*   Insight Builder는 **"무엇을(What) 쓸지"**를 결정합니다 (설계도).
*   Writer는 **"어떻게(How) 쓸지"**를 결정합니다 (문장력, 표현).
*   이 분업을 통해 **할루시네이션은 줄고, 콘텐츠의 깊이는 깊어집니다.**
