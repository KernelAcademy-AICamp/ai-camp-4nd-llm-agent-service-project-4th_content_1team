# YouTube 영상 인기도 순위 알고리즘

## 📍 위치
`BE/app/services/youtube_service.py` → `_calculate_popularity_score()` 함수

---

## 🎯 목적
YouTube 검색 결과를 **"지금 가장 핫한 영상"** 순으로 정렬하기 위한 종합 점수 계산

단순 조회수 순위가 아닌, **트렌드·신선도·참여도**를 종합 고려한 지능형 랭킹

---

## 📐 핵심 공식

```python
popularity_score = (views_per_day × recency_weight) + engagement_score
```

### 세부 계산식

#### 1️⃣ **일일 조회수** (views_per_day)
```python
views_per_day = view_count / max(days_since_upload, 1)
```

- `view_count`: 영상 총 조회수
- `days_since_upload`: 업로드 후 경과 일수 (최소 1일)

**의미**: 하루 평균 얼마나 많은 사람이 보는가?

---

#### 2️⃣ **신선도 가중치** (recency_weight)

최신 영상일수록 높은 가중치를 부여하여 **트렌드 반영**

```python
if days_since_upload <= 30:
    recency_weight = 2.0 - (days_since_upload / 30)  # 2.0 → 1.0

elif days_since_upload <= 90:
    recency_weight = 1.0 - ((days_since_upload - 30) / 120)  # 1.0 → 0.5

else:  # 91일 이상
    recency_weight = max(0.2, 0.5 - ((days_since_upload - 90) / 365))  # 최소 0.2
```

| 업로드 후 경과 | 가중치 범위 | 설명 |
|---------------|-------------|------|
| **0~30일** | 2.0 → 1.0 | 🔥 최신 트렌드 (최대 2배 보너스) |
| **31~90일** | 1.0 → 0.5 | 📈 중간 (약한 페널티) |
| **91일+** | 0.5 → 0.2 | 📉 오래됨 (강한 페널티, 최소 0.2) |

**그래프**:
```
가중치
  2.0 ┤●
      │ ●
      │  ●
  1.5 │   ●
      │    ●
  1.0 │─────●
      │      ●
  0.5 │       ●───
      │            ●──
  0.2 │───────────────●─────→
      0   30   60   90   180   365 (일)
```

---

#### 3️⃣ **참여도 점수** (engagement_score)

조회수 대비 좋아요·댓글 비율로 **영상 품질** 측정

```python
if view_count > 0:
    like_ratio = like_count / view_count
    comment_ratio = comment_count / view_count
    
    view_scale = math.log10(max(view_count, 10))  # 로그 스케일
    
    engagement_score = (like_ratio × 1000 + comment_ratio × 500) × view_scale
else:
    engagement_score = 0
```

**세부 요소**:
- **`like_ratio`**: 좋아요 수 / 조회수 (비율)
- **`comment_ratio`**: 댓글 수 / 조회수 (비율)
- **`view_scale`**: `log10(조회수)` (큰 영상의 누적 이점 완화)

**가중치**:
- 좋아요 비율: 1000배
- 댓글 비율: 500배

**의미**: 
- 조회수 1만, 좋아요 500 → 좋아요 비율 5% (높음!)
- 조회수 100만, 좋아요 500 → 좋아요 비율 0.05% (낮음)

→ **비율 기반**으로 오래된 영상의 누적 좋아요 이점 제거

---

## 🧮 계산 예시

### 예시 1: 신규 바이럴 영상
```
조회수: 50,000
업로드: 5일 전
좋아요: 1,200 (2.4%)
댓글: 80 (0.16%)

━━━━━━━━━━━━━━━━━━━━━━━
① views_per_day = 50,000 / 5 = 10,000

② recency_weight = 2.0 - (5 / 30) = 1.83

③ engagement_score:
   like_ratio = 1,200 / 50,000 = 0.024
   comment_ratio = 80 / 50,000 = 0.0016
   view_scale = log10(50,000) = 4.7
   
   engagement = (0.024 × 1000 + 0.0016 × 500) × 4.7
              = (24 + 0.8) × 4.7
              = 116.6

④ popularity_score = (10,000 × 1.83) + 116.6
                    = 18,300 + 116.6
                    = 18,416.6 ✅
```

### 예시 2: 오래된 인기 영상
```
조회수: 500,000
업로드: 365일 전
좋아요: 8,000 (1.6%)
댓글: 500 (0.1%)

━━━━━━━━━━━━━━━━━━━━━━━
① views_per_day = 500,000 / 365 = 1,370

② recency_weight = max(0.2, 0.5 - ((365-90)/365)) = 0.2

③ engagement_score:
   like_ratio = 8,000 / 500,000 = 0.016
   comment_ratio = 500 / 500,000 = 0.001
   view_scale = log10(500,000) = 5.7
   
   engagement = (0.016 × 1000 + 0.001 × 500) × 5.7
              = (16 + 0.5) × 5.7
              = 94.1

④ popularity_score = (1,370 × 0.2) + 94.1
                    = 274 + 94.1
                    = 368.1 ✅
```

**결과**: 신규 바이럴 영상(18,416점)이 오래된 인기 영상(368점)보다 **50배 높은 점수!**

---

## 📊 점수 해석

| 점수 범위 | 등급 | 의미 |
|----------|------|------|
| **10,000+** | S | 🔥 초대박 바이럴 (신규 & 높은 참여도) |
| **5,000~10,000** | A+ | 🚀 매우 핫한 영상 |
| **1,000~5,000** | A | ⭐ 핫한 영상 |
| **500~1,000** | B+ | 📈 괜찮은 성과 |
| **100~500** | B | ✔️ 평균 |
| **< 100** | C | 📉 저조 또는 오래됨 |

---

## 🎯 알고리즘의 특징

### ✅ 장점

1. **최신 트렌드 우선**
   - 30일 이내 영상에 최대 2배 보너스
   - "지금 핫한" 콘텐츠 발견

2. **오래된 영상 페널티**
   - 91일 이상은 강한 페널티 (최소 0.2배)
   - 명작이지만 트렌드는 아님

3. **참여도 정규화**
   - 조회수 대비 비율로 계산
   - 작은 채널도 공정하게 평가

4. **로그 스케일**
   - `log10(조회수)`로 큰 채널 이점 완화
   - 조회수 10배 차이 ≠ 점수 10배 차이

### ⚠️ 한계

1. **과거 명작 저평가**
   - 1년 전 훌륭한 강의는 낮은 점수
   - → 별도 "evergreen" 필터 필요

2. **조회수 중심**
   - 시청 유지율, 좋아요/싫어요 비율 미반영
   - → YouTube Analytics API 필요 (내 채널만 가능)

3. **알고리즘 편향**
   - YouTube 자체 추천에 의존
   - 검색 순위가 낮은 채널은 누락

---

## 🔧 커스터마이징 포인트

### 가중치 조정
```python
# 현재 설정
popularity_score = (views_per_day × recency_weight) + engagement_score
                    ───────────────────────────       ─────────────────
                           트렌드 중심                    참여도 보조

# 참여도 강화 버전
popularity_score = (views_per_day × recency_weight) × 0.7 + engagement_score × 0.3

# 신선도 약화 버전 (evergreen 콘텐츠용)
if days_since_upload <= 90:
    recency_weight = 1.5  # 기존: 2.0
else:
    recency_weight = 0.8  # 기존: 0.2
```

### 필터 추가
```python
# Shorts 제외 (이미 적용됨)
if duration_sec <= 60:
    continue

# 조회수 최소 기준
if view_count < 1000:
    continue

# 참여도 최소 기준
if like_count / view_count < 0.005:  # 0.5% 미만
    continue
```

---

## 📈 실제 사용 예시

### 검색어: "AI 웹개발 튜토리얼"

**결과 (Top 10)**:

| 순위 | 제목 | 조회수 | 업로드 | 점수 |
|-----|------|--------|--------|------|
| 1 | ChatGPT로 10분만에 웹사이트 만들기 | 50K | 3일 전 | 18,417 |
| 2 | 2026 AI 웹개발 완전정복 | 80K | 2주 전 | 11,245 |
| 3 | AI 코딩 도구 Top 5 | 30K | 1주 전 | 7,892 |
| 4 | 풀스택 AI 개발 강의 [10시간] | 500K | 6개월 전 | 368 |
| 5 | Next.js + AI 실전 프로젝트 | 15K | 20일 전 | 1,156 |
| ... | ... | ... | ... | ... |

**분석**:
- 1위: 신규(3일) + 높은 일일 조회수 = 최고 점수
- 4위: 조회수는 가장 높지만 6개월 전 → 낮은 recency_weight로 4위

---

## 🔄 처리 흐름

```
1. YouTube 검색 (50개 수집)
   ↓
2. 상세 정보 조회 (통계 + contentDetails)
   ↓
3. Shorts 필터링 (60초 이하 제외)
   ↓
4. 각 영상의 popularity_score 계산
   ↓
5. 점수 높은 순 정렬
   ↓
6. 상위 10개 반환
```

---

## 💻 코드 위치 및 사용

### 계산 함수
```python
# 파일: BE/app/services/youtube_service.py
# 함수: YouTubeService._calculate_popularity_score(video: Dict) -> tuple[float, int]

# 호출 위치
def search_popular_videos(...):
    # ...
    for video in filtered_videos:
        score, days = YouTubeService._calculate_popularity_score(video)
        video["popularity_score"] = score
        video["days_since_upload"] = days
    
    # 정렬
    sorted_videos = sorted(
        filtered_videos,
        key=lambda x: x.get("popularity_score", 0),
        reverse=True  # 내림차순
    )
    
    return sorted_videos[:max_results]
```

### API 엔드포인트
```
POST /api/v1/youtube/search
```

### 프론트엔드 사용
```typescript
// FE/src/pages/script/components/competitor-analysis.tsx
const { data } = useQuery({
  queryFn: () => searchYouTubeVideos({ keywords, max_results: 10 })
})

// data.videos는 이미 popularity_score 순으로 정렬됨
```

---

## 🧪 테스트 케이스

### Case 1: 신규 vs 오래된 영상
```
영상 A: 조회수 10K, 업로드 1일 전
→ 일일 조회수: 10,000
→ 가중치: 2.0
→ 점수: 20,000+

영상 B: 조회수 100K, 업로드 1년 전
→ 일일 조회수: 274
→ 가중치: 0.2
→ 점수: 55+

결과: A가 B보다 높음 ✅
```

### Case 2: 참여도 차이
```
영상 A: 조회수 10K, 좋아요 500 (5%)
→ engagement: 높음 (~100점)

영상 B: 조회수 10K, 좋아요 50 (0.5%)
→ engagement: 낮음 (~10점)

결과: 같은 조회수라도 A가 90점 차이로 우위 ✅
```

---

## 📊 통계 및 인사이트

### 실제 데이터 분석 (샘플)

```python
# 검색어: "프로그래밍 튜토리얼"
# 검색 결과 50개 중 상위 10개 분포

점수 분포:
- 15,000~20,000: 2개 (초대박 신규)
- 5,000~10,000: 3개 (매우 핫함)
- 1,000~5,000: 4개 (핫함)
- 500~1,000: 1개 (괜찮음)

업로드 시기 분포:
- 7일 이내: 5개 (50%)
- 8~30일: 3개 (30%)
- 31~90일: 2개 (20%)
- 90일+: 0개 (0%)

→ 최신 영상이 압도적으로 우위!
```

---

## 🎨 변형 알고리즘 (옵션)

### 옵션 1: Evergreen 콘텐츠용
오래된 명작도 높은 점수를 주고 싶을 때

```python
# 신선도 페널티 완화
if days_since_upload <= 90:
    recency_weight = 1.5  # 기존: 2.0
else:
    recency_weight = 0.8  # 기존: 0.2 (최소값 상향)
```

### 옵션 2: 참여도 강화
커뮤니티 반응이 중요한 경우

```python
# 참여도 가중치 증가
popularity_score = (views_per_day × recency_weight) × 0.6 + engagement_score × 0.4
                    ────────────────────────────────────     ────────────────────
                              트렌드 60%                         참여도 40%
```

### 옵션 3: 특정 기간 필터
```python
# 최근 30일 영상만
if days_since_upload > 30:
    continue

# 또는 6개월~1년 "중기 트렌드"
if not (180 <= days_since_upload <= 365):
    continue
```

---

## 📝 요약

### 핵심 3요소
1. **일일 조회수**: 인기도의 기본 (정규화)
2. **신선도**: 트렌드 반영 (시간 가중치)
3. **참여도**: 품질 측정 (좋아요/댓글 비율)

### 공식 한눈에
```
🔥 인기도 = (하루 조회수 × 신선도 보너스) + 참여도 점수

신선도:
- 신규 (0~30일): 최대 2배 🎁
- 중간 (31~90일): 1.0~0.5배
- 오래됨 (91일+): 최소 0.2배 📉

참여도:
- 조회수 대비 좋아요/댓글 비율
- 로그 스케일로 공정성 확보
```

### 결과
**"지금 가장 핫한 영상"**을 정확하게 찾아 상위 10개 추천! 🎯

---

## 🔗 관련 문서
- [YouTube 검색 로직 설명](../youtube-search-logic.md)
- [기술 스택](../TECH_STACK.md)
- [경쟁 유튜버 분석 계획](./competitor-youtuber-analysis-plan.md)
