# 오늘의 작업 계획 (2026-02-02)

## ✅ 완료된 작업
- [x] 전체 파이프라인 구현 (7개 노드)
- [x] Trend Scout → Planner → News Research → YT Fetcher → Competitor Analyzer → Insight Builder → Writer
- [x] 첫 통합 테스트 성공

---

## 🎯 오늘 해야 할 작업 (우선순위 순)

### 1. 프롬프트 튜닝 (30분) ⭐⭐⭐
**목표**: Fact 사용률 0% → 80%+

**작업 내용:**
- [ ] `writer.py` 프롬프트 수정
  - "반드시 Fact ID를 인용하라" 명시
  - "각 주장마다 fact-{id} 형식으로 출처 표기" 추가
  
- [ ] `insight_builder.py` 프롬프트 수정
  - "required_facts를 명확히 지정하라" 강조
  - "각 챕터마다 최소 2~3개 Fact 필수" 명시

**예상 효과:**
- Writer가 News Research의 팩트를 실제로 활용
- 근거 기반 대본 작성 실현

---

### 2. 주제 일관성 유지 (30분) ⭐⭐
**목표**: 입력 주제 "AI 반도체" → 출력도 "AI 반도체"

**작업 내용:**
- [ ] `planner.py` 프롬프트 수정
  - "원래 주제(topic)를 반드시 중심으로" 명시
  - "Trend Scout 결과는 보조 자료로만 활용" 추가
  
- [ ] `graph.py` State 전달 확인
  - Planner가 `topic`과 `trend_data`를 모두 받는지 확인
  - `topic`이 우선순위를 가지도록 설정

**예상 효과:**
- 사용자가 입력한 주제로 대본 생성
- Trend Scout는 "키워드 보강" 역할로 제한

---

### 3. Writer Phase 2 - Source Binding (2~3시간) ⭐⭐⭐
**목표**: Claims와 Facts 연결 추적

**작업 내용:**

#### 3-1. Schema 확장 (30분)
- [ ] `writer.py` Schema에 `ScriptClaim` 추가
  ```python
  class ScriptClaim(BaseModel):
      claim_text: str
      source_fact_ids: List[str]
      confidence: Literal["high", "medium", "low"]
  ```

- [ ] `ScriptBeat`에 `claims` 필드 추가
  ```python
  class ScriptBeat(BaseModel):
      ...
      claims: List[ScriptClaim] = Field(default=[])
  ```

#### 3-2. Writer 로직 수정 (1.5시간)
- [ ] LLM 프롬프트에 "각 주장마다 ScriptClaim 생성" 추가
- [ ] `_generate_script` 함수에서 Claims 추출 로직 구현
- [ ] Fact ID 검증 (존재하지 않는 ID 사용 시 경고)

#### 3-3. Quality Report 강화 (30분)
- [ ] `_build_quality_report` 함수 수정
  - 사용된 Fact ID 추출 (Claims에서)
  - 미사용 필수 Fact 계산
  - Fact 사용률(%) 추가

#### 3-4. 테스트 (30분)
- [ ] `test_script_gen_pipeline.py` 실행
- [ ] Quality Report에서 Fact 사용률 확인
- [ ] Claims가 올바른 Fact ID를 참조하는지 확인

**예상 효과:**
- "이 문장은 fact-abc123에서 나왔다" 추적 가능
- 팩트 체크 가능
- 신뢰도 향상

---

## 📋 작업 순서

**오전 (지금~1시)**
1. 프롬프트 튜닝 (30분)
2. 주제 일관성 유지 (30분)
3. 테스트 & 점심

**오후 (2시~5시)**
4. Writer Phase 2 - Schema 확장 (30분)
5. Writer Phase 2 - 로직 수정 (1.5시간)
6. Writer Phase 2 - Quality Report (30분)
7. 최종 테스트 (30분)

---

## 🎯 오늘의 성공 기준

- [ ] Fact 사용률 80% 이상
- [ ] 입력 주제와 출력 주제 일치
- [ ] Claims와 Facts 연결 추적 가능
- [ ] Quality Report에 상세 통계 표시

---

## 📝 메모

### 발견된 이슈
1. ~~Fact 사용률 0%~~ (프롬프트 튜닝으로 해결 예정)
2. ~~주제 변경 (AI 반도체 → 트럼프)~~ (Planner 프롬프트 수정으로 해결 예정)
3. Writer Phase 1은 MVP라서 Source Binding 없음 (Phase 2로 해결 예정)

### 나중에 할 작업 (내일 이후)
- YT Fetcher 실제 API 연동
- Competitor Analyzer 자막 분석
- FastAPI 엔드포인트 추가
- DB 저장 로직
