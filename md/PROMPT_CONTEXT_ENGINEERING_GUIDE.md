# 🎨 썸네일 생성 시스템 - 프롬프트 & 컨텍스트 엔지니어링 가이드

## 📋 목차
1. [개요](#개요)
2. [프롬프트 vs 컨텍스트 엔지니어링](#프롬프트-vs-컨텍스트-엔지니어링)
3. [시스템 워크플로우](#시스템-워크플로우)
4. [4인 에이전트 구성](#4인-에이전트-구성)
5. [핵심 구현 전략](#핵심-구현-전략)
6. [LangGraph 멀티에이전트 시스템](#langgraph-멀티에이전트-시스템)
7. [실전 코드 예시](#실전-코드-예시)
8. [UI/UX 고려사항](#uiux-고려사항)

---

## 개요

유튜브 썸네일 자동 생성 서비스에서 **프롬프트 엔지니어링**과 **컨텍스트 엔지니어링**을 활용하여, 사용자가 복잡한 기술 프롬프트를 몰라도 자연어 대화만으로 고품질 썸네일을 생성합니다.

### 핵심 목표
- ✅ 기술 프롬프트를 사용자 친화적인 한국어로 번역
- ✅ 사용자 피드백 무제한 반영 (만족할 때까지)
- ✅ 레퍼런스 이미지와 스크립트 컨텍스트 최대 활용
- ✅ **LangGraph 기반 4인 멀티에이전트 시스템**으로 고품질 보장

---

## 프롬프트 vs 컨텍스트 엔지니어링

### 🎯 프롬프트 엔지니어링
**"어떻게 AI에게 요청할 것인가"**

AI에게 주는 질문/지시문을 최적화하는 작업.

#### 본 시스템 적용 사례
```
✅ 기술 프롬프트 → 한국어 번역
❌ "A Korean news anchor, frontal medium shot, dark studio..."
✅ "어두운 뉴스룸에서 앵커가 정면을 바라보는 구도로 촬영할게요."

✅ 사용자 피드백 → 프롬프트 수정
"배경 밝게" → dark studio → bright studio

✅ 에이전트별 전문화된 프롬프트 템플릿
```

---

### 🗂️ 컨텍스트 엔지니어링
**"무엇을 AI에게 전달할 것인가"**

AI가 참조할 배경 정보를 설계/관리하는 작업.

#### 본 시스템 적용 사례
```python
# 컨텍스트 계층 구조
{
    "입력_컨텍스트": {
        "script_summary": "영상 스크립트 요약",
        "keywords": ["긴급", "속보"],
        "user_request": "긴박한 뉴스 느낌으로",
        "reference_images": ["ref1.jpg"]
    },
    "분석_컨텍스트": {
        "reference_analysis": {
            "composition": "정면 구도",
            "colors": ["#FF0000", "#000000"],
            "lighting": "dramatic side lighting"
        }
    },
    "피드백_컨텍스트": {
        "history": [
            {"feedback": "배경 밝게", "applied": "bright studio"},
            {"feedback": "인물 크게", "applied": "close-up"}
        ]
    }
}
```

**핵심**: 레퍼런스 이미지 분석, 스크립트 요약, 피드백 히스토리를 컨텍스트로 제공하여 에이전트가 더 정확한 결정을 하도록 함.

---

## 시스템 워크플로우

```
[사용자 입력]
레퍼런스 이미지 + 자연어 요청 ("밝은 느낌으로")
         ↓
[Copywriter Agent]
스크립트 요약 → 제목 3가지 생성
         ↓
[👤 사용자 선택/입력]
제목 확정
         ↓
[레퍼런스 이미지 분석]
비전 모델로 구도/색감/조명 추출
         ↓
[Prompt Specialist Agent]
Nano Banana Pro용 기술 프롬프트 생성
         ↓
[Interaction Agent]
기술 프롬프트 → 한국어 요약
         ↓
[👤 사용자 확인]
    ↙          ↘
[피드백]      [승인]
    ↓            ↓
(다시 Prompt  [Art Director]
 Specialist)  최종 검수
    ↓            ↓
(루프 반복)   [이미지 생성]
```

**핵심 특징**:
- **순환 루프**: 피드백 → 수정 → 확인 (무한 반복 가능)
- **Human-in-the-loop**: 사용자 확인 시점에서 대기
- **4인 전문 에이전트**: 각자 역할 분담

---

## 4인 에이전트 구성

### 1️⃣ Copywriter Agent (텍스트 작가)

**역할**: 스크립트 분석 → 썸네일 텍스트 생성

**입력 컨텍스트**:
- 스크립트 요약
- 키워드
- 사용자 톤 요청

**프롬프트 예시**:
```
당신은 유튜브 썸네일 텍스트 전문가입니다.

컨텍스트:
- 스크립트 요약: {summary}
- 키워드: {keywords}
- 사용자 요청: {user_request}

미션: 3가지 스타일 제목 생성
1. 의문형: "이게 가능해?"
2. 충격형: "긴급 속보!"
3. 요약형: "핵심 정리"

형식: 주제목 15자 이내, 부제목 10자 이내
```

---

### 2️⃣ Prompt Specialist Agent (프롬프트 전문가) ⭐

**역할**: 기술 프롬프트 생성 및 피드백 반영 수정

**2가지 모드**:

#### 모드 1: 초기 생성
```
입력 컨텍스트:
- 확정 텍스트: "긴급 속보! 충격 발표"
- 사용자 요청: "긴박한 뉴스 느낌"
- 레퍼런스 분석: {구도, 색감, 조명}
- Nano Banana Best Practices (필수 준수)

출력: Nano Banana Pro용 영어 프롬프트
```

#### 모드 2: 피드백 반영 수정
```
입력:
- 현재 프롬프트
- 사용자 피드백: "배경 더 밝게"

변환 로직:
"밝게" → lighting: dark → bright
"크게" → framing: medium shot → close-up
"색상" → color scheme 변경

출력: 수정된 프롬프트
```

**핵심**: 이 에이전트가 **순환 노드**가 되어 피드백 루프 담당!

---

### 3️⃣ Interaction Agent (소통 에이전트)

**역할**: 기술 프롬프트 ↔ 한국어 번역

**프롬프트 예시**:
```
기술 프롬프트:
"A Korean news anchor, frontal medium shot, dark studio 
with red emergency lighting, dramatic contrast..."

↓ 번역 규칙 ↓
- 기술 용어 제거: 85mm → 클로즈업
- 감성 표현: chiaroscuro → 명암 대비
- 반말 사용: ~할게요

출력:
"어두운 뉴스룸에서 앵커가 정면을 바라보는 구도로,
빨간 조명으로 긴박감을 연출할게요."
```

**Prompt Hiding**: 복잡한 프롬프트는 사용자에게 숨기고, 기획 의도만 전달!

---

### 4️⃣ Art Director Agent (최종 검수)

**역할**: 프롬프트 품질 보증

**체크리스트**:
- ✅ 텍스트와 비주얼 조화?
- ✅ 기술적 오류 없음?

---

## 핵심 구현 전략

### 1. 레퍼런스 이미지 분석 (컨텍스트 엔지니어링)

```python
import base64
from anthropic import Anthropic

async def analyze_reference_image(image_path: str) -> dict:
    """비전 모델로 레퍼런스 분석 → 컨텍스트 생성"""
    client = Anthropic()
    
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode()
    
    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": image_data
                    }
                },
                {
                    "type": "text",
                    "text": """이 썸네일을 분석하여 JSON 출력:
{
  "composition": "구도 (예: 정면, 3분할)",
  "dominant_colors": ["#FF0000", "#000000"],
  "lighting": "조명 스타일",
  "mood": "분위기"
}"""
                }
            ]
        }]
    )
    
    import json
    return json.loads(response.content[0].text)

# 활용
analysis = await analyze_reference_image("ref.jpg")
# → Prompt Specialist에게 컨텍스트로 전달
```

---

### 2. 피드백 히스토리 관리 (컨텍스트 누적)

```python
class FeedbackHistory:
    def __init__(self):
        self.history = []
    
    def add(self, feedback: str, applied: str):
        self.history.append({
            "iteration": len(self.history) + 1,
            "feedback": feedback,
            "applied": applied
        })
    
    def get_context(self) -> str:
        """누적 피드백을 컨텍스트로 변환"""
        if not self.history:
            return "피드백 없음"
        
        lines = ["**피드백 히스토리**:"]
        for h in self.history:
            lines.append(f"{h['iteration']}. \"{h['feedback']}\" → {h['applied']}")
        return "\n".join(lines)

# 사용
fb = FeedbackHistory()
fb.add("배경 밝게", "bright studio")
fb.add("인물 크게", "close-up")

context = fb.get_context()
# 출력:
# **피드백 히스토리**:
# 1. "배경 밝게" → bright studio
# 2. "인물 크게" → close-up
```

---

## LangGraph 멀티에이전트 시스템

### 🤔 LangGraph가 뭔가요?

**LangGraph**는 여러 AI 에이전트가 협업하는 **상태 기반 워크플로우**를 만드는 프레임워크입니다.

#### 왜 필요한가?

일반 Python 코드로 멀티에이전트 구현 시:
```python
# ❌ 수동으로 상태 전달 (복잡함)
text = copywriter(script)
selected = user_select(text)
analysis = analyze_ref(images)
prompt = specialist(selected, analysis)  # 매번 전달
korean = interaction(prompt)
if feedback:
    prompt = specialist(prompt, feedback)  # 다시 전달
    korean = interaction(prompt)
    # 반복...
```

LangGraph 사용 시:
```python
# ✅ State 자동 관리 (간단함)
app = workflow.compile()
result = app.invoke(initial_state)
# State가 자동으로 각 노드에 전달/업데이트
# 순환 루프도 자동 처리
```

---

### 📦 LangGraph 핵심 개념 3가지

#### 1. State (상태)
모든 에이전트가 공유하는 데이터 저장소.

```python
from typing import TypedDict, List, Dict

class ThumbnailState(TypedDict):
    # 입력
    script_summary: str
    keywords: List[str]
    user_natural_request: str
    reference_images: List[str]
    
    # 중간 결과
    text_options: List[Dict]
    selected_text: Dict
    reference_analysis: Dict
    
    # 프롬프트
    technical_prompt: str      # Prompt Specialist 생성
    korean_summary: str         # Interaction 번역
    
    # 피드백
    user_feedback: str
    feedback_history: List[Dict]
    is_confirmed: bool
    
    # 최종
    final_prompt: str
    generated_image_path: str
```

**동작 방식**:
- 각 노드는 State를 받음
- 노드가 State 수정
- 수정된 State가 다음 노드로 자동 전달

---

#### 2. Node (노드)
각 에이전트의 실행 함수. State를 입력받아 수정 후 반환.

```python
def copywriter_node(state: ThumbnailState) -> ThumbnailState:
    """텍스트 생성"""
    # State에서 필요한 데이터 읽기
    summary = state["script_summary"]
    keywords = state["keywords"]
    
    # LLM 호출하여 텍스트 생성
    text_options = generate_text(summary, keywords)
    
    # State 업데이트
    state["text_options"] = text_options
    
    return state  # 수정된 State 반환
```

**핵심**: 함수 시그니처는 항상 `(state) -> state`

---

#### 3. Edge (엣지)
노드 간 연결. 실행 순서 정의.

**2가지 타입**:

##### A. 순차 엣지 (무조건 다음으로)
```python
workflow.add_edge("copywriter", "prompt_specialist")
# copywriter 완료 → 무조건 prompt_specialist 실행
```

##### B. 조건부 엣지 (상황에 따라 분기)
```python
def check_confirmation(state):
    if state["is_confirmed"]:
        return "art_director"  # 승인 → 다음
    else:
        return "prompt_specialist"  # 피드백 → 다시

workflow.add_conditional_edges(
    "interaction",  # 이 노드 후
    check_confirmation,  # 조건 함수
    {
        "art_director": "art_director",
        "prompt_specialist": "prompt_specialist"  # 루프!
    }
)
```

---

### 🔄 피드백 루프 구현 원리

**핵심**: 조건부 엣지로 순환 구조 만들기

```
Prompt Specialist → Interaction → 사용자 확인
        ↑                              ↓
        └──────── 피드백 있으면 ─────────┘
                (다시 Prompt Specialist)
```

**코드**:
```python
workflow.add_conditional_edges(
    "interaction",
    lambda state: "art_director" if state["is_confirmed"] 
                  else "prompt_specialist",
    {
        "art_director": "art_director",
        "prompt_specialist": "prompt_specialist"  # 자기 자신으로!
    }
)
```

**동작**:
1. Prompt Specialist: 프롬프트 생성
2. Interaction: 한국어 번역
3. 사용자 확인 대기
4. 피드백 입력 시: State에 `user_feedback` 추가, `is_confirmed=False`
5. 조건부 엣지: `is_confirmed=False` → Prompt Specialist로 돌아감
6. Prompt Specialist: 피드백 반영하여 프롬프트 수정
7. 2번부터 반복...

**무한 루프 가능**: 사용자가 `is_confirmed=True` 설정할 때까지 계속 반복!

---

### 🛑 Human-in-the-loop (사용자 입력 대기)

**문제**: 사용자 확인을 기다려야 하는데 어떻게?

**해결**: `interrupt_before` 사용

```python
workflow.add_interrupt("interaction")
# interaction 노드 실행 후 자동으로 멈춤
```

**실행 흐름**:
```python
# 1. 초기 실행
app = workflow.compile()
result = app.invoke(initial_state)
# → interaction까지 실행 후 STOP

# 2. 사용자에게 korean_summary 보여줌
print(result["korean_summary"])
# "어두운 뉴스룸에서..."

# 3. 사용자 입력 대기
user_input = input("피드백 또는 '확인': ")

# 4. State 업데이트
if user_input == "확인":
    result["is_confirmed"] = True
else:
    result["user_feedback"] = user_input
    result["is_confirmed"] = False

# 5. 계속 실행
result = app.invoke(result)
# → 조건부 엣지 판단 → 다음 노드 실행
```

---

### 📊 전체 Graph 구성 코드

```python
from langgraph.graph import StateGraph, END

# 1. State 정의
class ThumbnailState(TypedDict):
    # ... (위에 정의한 대로)
    pass

# 2. Graph 초기화
workflow = StateGraph(ThumbnailState)

# 3. 노드 추가
workflow.add_node("copywriter", copywriter_node)
workflow.add_node("analyze_reference", analyze_reference_node)
workflow.add_node("prompt_specialist", prompt_specialist_node)
workflow.add_node("interaction", interaction_node)
workflow.add_node("art_director", art_director_node)

# 4. 순차 엣지
workflow.add_edge("copywriter", "analyze_reference")
workflow.add_edge("analyze_reference", "prompt_specialist")
workflow.add_edge("prompt_specialist", "interaction")

# 5. 조건부 엣지 (피드백 루프!)
def check_confirmation(state: ThumbnailState):
    if state["is_confirmed"]:
        return "art_director"
    else:
        return "prompt_specialist"  # 순환!

workflow.add_conditional_edges(
    "interaction",
    check_confirmation,
    {
        "art_director": "art_director",
        "prompt_specialist": "prompt_specialist"
    }
)

workflow.add_edge("art_director", END)

# 6. Human-in-the-loop
workflow.add_interrupt("interaction")

# 7. 시작점
workflow.set_entry_point("copywriter")

# 8. 컴파일
app = workflow.compile()
```

---

### 🎬 실행 시나리오

```python
# 초기 State
initial_state = {
    "script_summary": "긴급 뉴스 발표",
    "keywords": ["속보", "충격"],
    "user_natural_request": "긴박한 느낌으로",
    "reference_images": ["ref.jpg"],
    "is_confirmed": False
}

# === 1회차 실행 ===
result = app.invoke(initial_state)
# Copywriter → Analyze → Prompt Specialist → Interaction
# → STOP (interrupt)

print(result["korean_summary"])
# "어두운 뉴스룸에서 앵커가..."

# 사용자 피드백
result["user_feedback"] = "배경 더 밝게"
result["is_confirmed"] = False

# === 2회차 실행 ===
result = app.invoke(result)
# Prompt Specialist (수정) → Interaction → STOP

print(result["korean_summary"])
# "밝은 스튜디오에서 앵커가..."

# 사용자 승인
result["is_confirmed"] = True

# === 3회차 실행 ===
result = app.invoke(result)
# Art Director → END

print(result["final_prompt"])
# "A Korean news anchor, bright studio..."
```

---

## 실전 코드 예시

### 노드 구현

#### 1. Copywriter Node

```python
from anthropic import Anthropic

def copywriter_node(state: ThumbnailState) -> ThumbnailState:
    client = Anthropic()
    
    prompt = f"""
스크립트: {state["script_summary"]}
키워드: {state["keywords"]}

3가지 스타일 제목을 JSON으로:
{{"options": [{{"style": "의문형", "main": "...", "sub": "..."}}]}}
"""
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        messages=[{"role": "user", "content": prompt}]
    )
    
    import json
    result = json.loads(response.content[0].text)
    state["text_options"] = result["options"]
    
    return state
```

#### 2. Prompt Specialist Node (핵심!)

```python
def prompt_specialist_node(state: ThumbnailState) -> ThumbnailState:
    client = Anthropic()
    
    is_initial = not state.get("technical_prompt")
    
    if is_initial:
        # 초기 생성
        prompt = f"""
텍스트: {state["selected_text"]}
요청: {state["user_natural_request"]}
레퍼런스: {state["reference_analysis"]}

Nano Banana Pro 프롬프트 생성.
"""
    else:
        # 수정
        prompt = f"""
현재: {state["technical_prompt"]}
피드백: {state["user_feedback"]}

수정된 프롬프트 생성.
"""
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        messages=[{"role": "user", "content": prompt}]
    )
    
    state["technical_prompt"] = response.content[0].text
    
    # 피드백 히스토리 추가
    if not is_initial:
        if "feedback_history" not in state:
            state["feedback_history"] = []
        state["feedback_history"].append({
            "feedback": state["user_feedback"],
            "applied": "수정됨"
        })
        state["user_feedback"] = ""
    
    return state
```

#### 3. Interaction Node

```python
def interaction_node(state: ThumbnailState) -> ThumbnailState:
    client = Anthropic()
    
    prompt = f"""
기술 프롬프트: {state["technical_prompt"]}

한국어로 번역 (2-3문장, 반말)
"""
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        messages=[{"role": "user", "content": prompt}]
    )
    
    state["korean_summary"] = response.content[0].text
    return state
```

---

## UI/UX 고려사항

### 1. 피드백 히스토리 표시

```python
# State에 저장된 히스토리
feedback_history = [
    {"feedback": "배경 밝게", "applied": "bright studio"},
    {"feedback": "인물 크게", "applied": "close-up"}
]

# UI 표시
"""
💬 수정 기록
1️⃣ "배경 밝게" → 밝은 스튜디오로 변경
2️⃣ "인물 크게" → 클로즈업으로 변경
"""
```

### 2. 비정상 루프 감지

```python
def detect_loop(history: list) -> dict:
    if len(history) < 3:
        return None
    
    recent = [h["feedback"] for h in history[-3:]]
    if len(set(recent)) == 1:  # 같은 피드백 3번
        return {
            "warning": "같은 요청이 반복되고 있어요",
            "suggestion": "더 구체적으로 설명해주세요"
        }
    return None
```

### 3. UI 목업

```
┌─────────────────────────────────┐
│ 썸네일 미리보기                  │
│ "긴급 속보! 충격적 발표"         │
│ [이미지 영역]                    │
├─────────────────────────────────┤
│ 💬 AI가 이렇게 만들 예정이에요:  │
│ 밝은 스튜디오에서 앵커가 정면을  │
│ 응시하는 클로즈업 구도로...      │
│                                 │
│ 🔄 수정 기록:                   │
│ 1. "배경 밝게" → 변경됨          │
│ 2. "인물 크게" → 변경됨          │
├─────────────────────────────────┤
│ 추가로 수정할 부분이 있나요?     │
│ ┌─────────────────────────────┐ │
│ │ 예: 색감 좀 더 따뜻하게      │ │
│ └─────────────────────────────┘ │
│ [← 이전] [✅ 이대로 생성하기]    │
└─────────────────────────────────┘
```

---

## 정리

### 프롬프트 엔지니어링 활용
- ✅ Prompt Specialist: 기술 프롬프트 생성
- ✅ Interaction: 한국어 번역
- ✅ 피드백 → 프롬프트 수정 로직

### 컨텍스트 엔지니어링 활용
- ✅ 레퍼런스 이미지 분석
- ✅ 스크립트 요약
- ✅ 피드백 히스토리 누적

### LangGraph 멀티에이전트
- ✅ State 자동 관리
- ✅ 조건부 엣지로 피드백 루프 구현
- ✅ Human-in-the-loop으로 사용자 확인 대기

**핵심**: 4인 에이전트가 LangGraph State를 공유하며 협업, 사용자 피드백을 무제한 반영!