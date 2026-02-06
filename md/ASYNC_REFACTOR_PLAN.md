# Async 리팩토링 작업 계획

## 📋 개요
AI Agent 파이프라인의 성능 개선을 위해 동기(sync) 함수를 비동기(async)로 전환합니다.

---

## 🎯 목표
- LLM 호출 대기 시간 동안 다른 작업 처리 가능하게 함
- 전체 파이프라인 실행 시간 단축
- Celery Worker와의 호환성 유지

---

## 📁 수정 대상 파일

| 파일 | 수정 내용 | 우선순위 |
|:---|:---|:---|
| `BE/src/script_gen/nodes/planner.py` | `def` → `async def`, `invoke()` → `ainvoke()` | 1순위 |
| `BE/src/script_gen/nodes/writer.py` | 동일 | 2순위 |
| `BE/src/script_gen/graph.py` | 노드 호출에 `await` 적용 | 3순위 |
| `BE/src/script_gen/nodes/news_research.py` | HTTP 요청 비동기화 (httpx/aiohttp) | 4순위 |

---

## 🔧 세부 작업

### 1. Planner 노드 (`planner.py`)
```python
# Before
def run_planner(state: PlannerState) -> PlannerState:
    result = llm.invoke(prompt)
    
# After
async def run_planner(state: PlannerState) -> PlannerState:
    result = await llm.ainvoke(prompt)
```

### 2. Writer 노드 (`writer.py`)
```python
# Before
def run_writer(state: WriterState) -> WriterState:
    result = llm.invoke(prompt)
    
# After
async def run_writer(state: WriterState) -> WriterState:
    result = await llm.ainvoke(prompt)
```

### 3. Graph 수정 (`graph.py`)
```python
# Before
result = run_planner(state)

# After
result = await run_planner(state)
```

### 4. News Research 이미지 다운로드 (`news_research.py`)

#### 현재 문제점 (동기 방식)
```python
import requests

# 이미지 10개를 순차적으로 다운로드 → 느림!
for image_url in image_urls:
    response = requests.get(image_url)  # 하나씩 대기
    save_image(response.content)
# 예: 이미지당 2초 × 10개 = 20초
```

#### 개선안 (비동기 방식)
```python
import httpx
import asyncio

async def download_image(client, url):
    response = await client.get(url)
    return response.content

async def download_all_images(image_urls):
    async with httpx.AsyncClient() as client:
        # 모든 이미지 동시 다운로드!
        tasks = [download_image(client, url) for url in image_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
# 예: 10개 동시 다운로드 = 2~3초
```

#### Rate Limit 적용 (사이트 차단 방지)
```python
# 동시 다운로드 수 제한
download_semaphore = asyncio.Semaphore(5)  # 최대 5개 동시

async def download_with_limit(client, url):
    async with download_semaphore:
        response = await client.get(url)
        return response.content
```

#### 예상 성능 개선
| 항목 | Before (동기) | After (비동기) |
|:---|:---|:---|
| 이미지 10개 다운로드 | ~20초 | ~3초 |
| 이미지 분석 (LLM) | 순차 처리 | 병렬 처리 가능 |

---

## ⚠️ 주의사항

### Rate Limit 대응
```python
import asyncio

# Semaphore로 동시 LLM 호출 수 제한
llm_semaphore = asyncio.Semaphore(3)  # 최대 3개 동시 호출

async def call_llm_with_limit(prompt):
    async with llm_semaphore:
        return await llm.ainvoke(prompt)
```

### Celery 통합
```python
# worker.py
def task_generate_script(request):
    # Celery task에서 async 함수 호출
    result = asyncio.run(generate_script_async(request))
    return result
```

---

## ✅ 체크리스트

- [ ] Planner 노드 async 전환
- [ ] Writer 노드 async 전환  
- [ ] Graph에 await 적용
- [ ] Celery worker 호환성 테스트
- [ ] 전체 파이프라인 실행 테스트
- [ ] Rate Limit 테스트

---

## 📝 참고사항
- LangChain의 `ainvoke()`는 기본 제공됨
- 기존 동기 버전은 백업 유지
- 단계별로 테스트하며 진행

---

**작성일:** 2026-02-06
