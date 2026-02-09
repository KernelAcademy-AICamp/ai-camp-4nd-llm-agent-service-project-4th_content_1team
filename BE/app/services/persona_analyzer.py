"""
페르소나 규칙 기반 해석

데이터 기반으로 채널 특성을 해석하는 규칙 기반 분석기입니다.
LLM 없이 동작하며, 정해진 기준에 따라 해석을 생성합니다.

해석 4가지:
1. 채널 규모 (구독자 수 기준)
2. 시청자층 (연령대, 성별, 지역)
3. 조회수 일관성 (변동계수)
4. 참여도 (좋아요율, 댓글율)
"""
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class Interpretation:
    """해석 결과 데이터 클래스"""
    signal: str      # 데이터 신호 (예: "구독자 5,000명")
    interpretation: str  # 해석 (예: "성장 초기 단계의 소형 채널")
    category: str    # 분류 (예: "small")
    confidence: str  # 신뢰도: high, medium, low


# =============================================================================
# 1. 채널 규모 해석
# =============================================================================

def analyze_channel_tier(subscriber_count: int) -> Interpretation:
    """
    구독자 수 기준 채널 규모 해석.

    | 구독자       | 티어 | 해석                          |
    |--------------|------|-------------------------------|
    | < 1,000      | 신생 | 이제 막 시작한 채널           |
    | 1,000~10,000 | 소형 | 성장 초기 단계                |
    | 10,000~100,000 | 중형 | 안정적인 시청자층 확보      |
    | > 100,000    | 대형 | 영향력 있는 채널              |
    """
    if subscriber_count < 1_000:
        return Interpretation(
            signal=f"구독자 {subscriber_count:,}명",
            interpretation="이제 막 시작한 신생 채널입니다. 초기 콘텐츠 방향을 잡아가는 단계로, 다양한 시도를 통해 채널 정체성을 확립해 나가는 것이 중요합니다.",
            category="emerging",
            confidence="high",
        )
    elif subscriber_count < 10_000:
        return Interpretation(
            signal=f"구독자 {subscriber_count:,}명",
            interpretation="성장 초기 단계의 소형 채널입니다. 핵심 시청자층이 형성되기 시작했으며, 꾸준한 업로드와 시청자 소통이 성장의 열쇠입니다.",
            category="small",
            confidence="high",
        )
    elif subscriber_count < 100_000:
        return Interpretation(
            signal=f"구독자 {subscriber_count:,}명",
            interpretation="안정적인 시청자층을 확보한 중형 채널입니다. 명확한 채널 정체성이 있으며, 브랜드 협업이나 수익화를 본격적으로 고려할 수 있는 단계입니다.",
            category="medium",
            confidence="high",
        )
    else:
        return Interpretation(
            signal=f"구독자 {subscriber_count:,}명",
            interpretation="영향력 있는 대형 채널입니다. 탄탄한 팬덤과 높은 인지도를 바탕으로 트렌드를 선도하거나 다양한 사업 확장이 가능한 단계입니다.",
            category="large",
            confidence="high",
        )


# =============================================================================
# 2. 시청자층 해석
# =============================================================================

@dataclass
class AudienceData:
    """시청자 데이터"""
    age_group: str  # "18-24", "25-34", etc.
    gender: str     # "male", "female"
    percentage: float


@dataclass
class GeoData:
    """지역별 시청자 데이터"""
    country: str    # "KR", "US", etc.
    percentage: float


def analyze_audience(
    audience_data: List[AudienceData],
    geo_data: List[GeoData],
) -> Interpretation:
    """
    시청자층 해석.

    - 연령대: 가장 높은 비율의 연령대
    - 성별: 남성 >70% → 남성 중심, 여성 >70% → 여성 중심
    - 지역: KR >80% → 국내 중심
    """
    if not audience_data and not geo_data:
        return Interpretation(
            signal="시청자 데이터 없음",
            interpretation="아직 시청자 분석을 위한 충분한 데이터가 수집되지 않았습니다.",
            category="unknown",
            confidence="low",
        )

    signals = []
    interpretations = []

    # 연령대 분석
    if audience_data:
        # 연령대별 합산
        age_totals = {}
        gender_totals = {"male": 0, "female": 0}

        for item in audience_data:
            age_totals[item.age_group] = age_totals.get(item.age_group, 0) + item.percentage
            if item.gender in gender_totals:
                gender_totals[item.gender] += item.percentage

        # 가장 높은 연령대
        if age_totals:
            top_age = max(age_totals, key=age_totals.get)
            top_age_pct = age_totals[top_age]
            age_label = _format_age_label(top_age)
            signals.append(f"주 연령대: {age_label} ({top_age_pct:.0f}%)")
            interpretations.append(f"주 시청층은 {age_label}입니다.")

        # 성별 비율
        total_gender = sum(gender_totals.values())
        if total_gender > 0:
            male_ratio = gender_totals["male"] / total_gender * 100
            female_ratio = gender_totals["female"] / total_gender * 100

            if male_ratio >= 70:
                signals.append(f"남성 {male_ratio:.0f}%")
                interpretations.append("남성 시청자가 압도적으로 많습니다.")
            elif female_ratio >= 70:
                signals.append(f"여성 {female_ratio:.0f}%")
                interpretations.append("여성 시청자가 압도적으로 많습니다.")
            elif male_ratio >= 55:
                signals.append(f"남성 {male_ratio:.0f}% / 여성 {female_ratio:.0f}%")
                interpretations.append("남성 시청자가 다소 많은 편입니다.")
            elif female_ratio >= 55:
                signals.append(f"여성 {female_ratio:.0f}% / 남성 {male_ratio:.0f}%")
                interpretations.append("여성 시청자가 다소 많은 편입니다.")
            else:
                signals.append(f"남성 {male_ratio:.0f}% / 여성 {female_ratio:.0f}%")
                interpretations.append("성별 비율이 균형 잡혀 있습니다.")

    # 지역 분석
    if geo_data:
        top_country = max(geo_data, key=lambda x: x.percentage)
        country_name = _get_country_name(top_country.country)

        if top_country.country == "KR" and top_country.percentage >= 80:
            signals.append(f"국내 시청자 {top_country.percentage:.0f}%")
            interpretations.append("국내 시청자 중심의 채널입니다.")
        elif top_country.country == "KR" and top_country.percentage >= 50:
            signals.append(f"국내 {top_country.percentage:.0f}%")
            interpretations.append("국내 시청자가 주를 이루지만 해외 시청자도 있습니다.")
        else:
            signals.append(f"{country_name} {top_country.percentage:.0f}%")
            interpretations.append(f"{country_name} 시청자가 가장 많습니다.")

    return Interpretation(
        signal=" / ".join(signals) if signals else "데이터 부족",
        interpretation=" ".join(interpretations) if interpretations else "분석 불가",
        category="audience_profile",
        confidence="high" if len(audience_data) >= 7 else "medium",
    )


def _format_age_label(age_group: str) -> str:
    """연령대 라벨 변환"""
    mapping = {
        "13-17": "10대",
        "18-24": "20대 초반",
        "25-34": "20대 후반~30대 초반",
        "35-44": "30대 후반~40대 초반",
        "45-54": "40대 후반~50대 초반",
        "55-64": "50대 후반~60대 초반",
        "65-": "65세 이상",
    }
    return mapping.get(age_group, age_group)


def _get_country_name(country_code: str) -> str:
    """국가 코드 -> 이름"""
    mapping = {
        "KR": "한국",
        "US": "미국",
        "JP": "일본",
        "CN": "중국",
        "TW": "대만",
        "VN": "베트남",
        "TH": "태국",
        "ID": "인도네시아",
        "GB": "영국",
        "DE": "독일",
    }
    return mapping.get(country_code, country_code)


# =============================================================================
# 3. 조회수 일관성 해석
# =============================================================================

@dataclass
class VideoStatsData:
    """영상 통계 데이터"""
    video_id: str
    title: str
    view_count: int
    like_count: int
    comment_count: int
    duration_seconds: int


def analyze_view_consistency(video_stats: List[VideoStatsData]) -> Interpretation:
    """
    조회수 일관성 해석 (변동계수 기반).

    변동계수(CV) = 표준편차 / 평균
    | < 0.5   | 안정적 | 구독자 기반 시청, 일관된 성과    |
    | 0.5~1.0 | 보통   | 주제에 따라 성과 달라짐          |
    | > 1.0   | 불안정 | 편차 큼, 바이럴 의존             |
    """
    if not video_stats or len(video_stats) < 5:
        return Interpretation(
            signal="영상 수 부족",
            interpretation="일관성 분석을 위한 충분한 영상 데이터가 없습니다. 최소 5개 이상의 영상이 필요합니다.",
            category="insufficient_data",
            confidence="low",
        )

    views = [v.view_count for v in video_stats if v.view_count > 0]
    if not views:
        return Interpretation(
            signal="조회수 데이터 없음",
            interpretation="조회수 데이터를 확인할 수 없습니다.",
            category="no_data",
            confidence="low",
        )

    # 변동계수 계산
    import statistics
    mean_views = statistics.mean(views)
    std_views = statistics.stdev(views) if len(views) > 1 else 0
    cv = std_views / mean_views if mean_views > 0 else 0

    # 평균 조회수 포맷
    avg_str = _format_number(int(mean_views))

    if cv < 0.5:
        return Interpretation(
            signal=f"평균 조회수 {avg_str}회 / 변동계수 {cv:.2f}",
            interpretation="조회수가 매우 안정적입니다. 구독자 기반의 충성도 높은 시청층이 있으며, 콘텐츠 주제나 품질이 일관되게 유지되고 있습니다.",
            category="stable",
            confidence="high",
        )
    elif cv < 1.0:
        return Interpretation(
            signal=f"평균 조회수 {avg_str}회 / 변동계수 {cv:.2f}",
            interpretation="조회수가 주제에 따라 다소 변동합니다. 특정 주제가 더 잘 되는 경향이 있으며, 인기 주제를 파악하여 전략적으로 활용하면 좋습니다.",
            category="moderate",
            confidence="high",
        )
    else:
        return Interpretation(
            signal=f"평균 조회수 {avg_str}회 / 변동계수 {cv:.2f}",
            interpretation="조회수 편차가 큽니다. 일부 영상이 바이럴되거나, 알고리즘 노출에 따라 성과가 크게 달라지는 패턴입니다. 히트작의 공통점을 분석하면 도움이 됩니다.",
            category="volatile",
            confidence="high",
        )


def _format_number(n: int) -> str:
    """숫자 포맷 (1,000 → 1천, 10,000 → 1만)"""
    if n >= 100_000_000:
        return f"{n / 100_000_000:.1f}억"
    elif n >= 10_000:
        return f"{n / 10_000:.1f}만"
    elif n >= 1_000:
        return f"{n / 1_000:.1f}천"
    else:
        return str(n)


# =============================================================================
# 4. 참여도 해석
# =============================================================================

def analyze_engagement(video_stats: List[VideoStatsData]) -> Interpretation:
    """
    참여도 해석 (좋아요율, 댓글율).

    좋아요율 = (좋아요 / 조회수) × 100
    | > 5%    | 매우 높음 | 열성 팬층, 강한 공감/지지       |
    | 3~5%    | 양호      | 좋은 참여도                      |
    | < 3%    | 평균      | 일반적인 수준                    |

    댓글율 = (댓글 / 조회수) × 100
    | > 1%    | 높음     | 활발한 커뮤니티, 토론 유발       |
    | 0.5~1%  | 적당     | 적절한 소통                      |
    | < 0.5%  | 낮음     | 정보 소비 위주, 소통 적음        |
    """
    if not video_stats:
        return Interpretation(
            signal="데이터 없음",
            interpretation="참여도 분석을 위한 데이터가 없습니다.",
            category="no_data",
            confidence="low",
        )

    # 전체 합산
    total_views = sum(v.view_count for v in video_stats)
    total_likes = sum(v.like_count for v in video_stats)
    total_comments = sum(v.comment_count for v in video_stats)

    if total_views == 0:
        return Interpretation(
            signal="조회수 0",
            interpretation="조회수가 없어 참여도를 계산할 수 없습니다.",
            category="no_views",
            confidence="low",
        )

    like_rate = (total_likes / total_views) * 100
    comment_rate = (total_comments / total_views) * 100

    signals = [f"좋아요율 {like_rate:.1f}%", f"댓글율 {comment_rate:.2f}%"]
    interpretations = []

    # 좋아요율 해석
    if like_rate >= 5:
        interpretations.append("좋아요율이 매우 높아 열성적인 팬층이 있습니다.")
    elif like_rate >= 3:
        interpretations.append("좋아요율이 양호하며 시청자 반응이 좋습니다.")
    else:
        interpretations.append("좋아요율은 평균적인 수준입니다.")

    # 댓글율 해석
    if comment_rate >= 1:
        interpretations.append("댓글이 활발하여 커뮤니티 형성이 잘 되어 있습니다.")
    elif comment_rate >= 0.5:
        interpretations.append("적절한 수준의 댓글 참여가 있습니다.")
    else:
        interpretations.append("댓글은 적은 편으로, 주로 정보 소비 목적의 시청자가 많습니다.")

    # 종합 카테고리 결정
    if like_rate >= 5 and comment_rate >= 1:
        category = "highly_engaged"
    elif like_rate >= 3 or comment_rate >= 0.5:
        category = "moderately_engaged"
    else:
        category = "low_engagement"

    return Interpretation(
        signal=" / ".join(signals),
        interpretation=" ".join(interpretations),
        category=category,
        confidence="high" if len(video_stats) >= 10 else "medium",
    )


# =============================================================================
# 5. 최적 영상 길이 해석
# =============================================================================

def analyze_optimal_duration(video_stats: List[VideoStatsData]) -> Interpretation:
    """
    영상 길이별 성과를 분석하여 최적 길이 도출.

    구간 분류:
    | 구간       | 라벨       |
    |-----------|-----------|
    | ~300초     | ~5분      |
    | 300~600   | 5~10분    |
    | 600~1200  | 10~20분   |
    | 1200~1800 | 20~30분   |
    | 1800~     | 30분 이상  |

    로직:
    1. 각 구간별 영상 수, 평균 조회수 계산
    2. 영상이 2개 이상인 구간 중 평균 조회수가 가장 높은 구간 = 최적 길이
    3. 해당 구간의 라벨을 반환
    """
    if not video_stats or len(video_stats) < 5:
        return Interpretation(
            signal="영상 수 부족",
            interpretation="최적 길이 분석을 위한 충분한 영상 데이터가 없습니다.",
            category="insufficient_data",
            confidence="low",
        )

    # 유효한 영상만 필터링 (duration > 0, view_count > 0)
    valid_videos = [
        v for v in video_stats
        if v.duration_seconds and v.duration_seconds > 0 and v.view_count > 0
    ]

    if len(valid_videos) < 5:
        return Interpretation(
            signal="유효 데이터 부족",
            interpretation="영상 길이 정보가 충분하지 않아 분석할 수 없습니다.",
            category="insufficient_data",
            confidence="low",
        )

    # 구간 정의
    duration_ranges = [
        (0, 300, "~5분"),
        (300, 600, "5~10분"),
        (600, 1200, "10~20분"),
        (1200, 1800, "20~30분"),
        (1800, float('inf'), "30분 이상"),
    ]

    # 구간별 집계
    range_stats = {}
    for min_sec, max_sec, label in duration_ranges:
        videos_in_range = [
            v for v in valid_videos
            if min_sec <= v.duration_seconds < max_sec
        ]
        if videos_in_range:
            avg_views = sum(v.view_count for v in videos_in_range) / len(videos_in_range)
            range_stats[label] = {
                "count": len(videos_in_range),
                "avg_views": avg_views,
            }

    if not range_stats:
        return Interpretation(
            signal="분석 불가",
            interpretation="영상 길이 데이터를 분석할 수 없습니다.",
            category="no_data",
            confidence="low",
        )

    # 영상 2개 이상인 구간 중 평균 조회수가 가장 높은 구간
    valid_ranges = {k: v for k, v in range_stats.items() if v["count"] >= 2}

    if not valid_ranges:
        # 2개 이상인 구간이 없으면 가장 영상 수 많은 구간
        best_range = max(range_stats.keys(), key=lambda k: range_stats[k]["count"])
        stats = range_stats[best_range]
    else:
        best_range = max(valid_ranges.keys(), key=lambda k: valid_ranges[k]["avg_views"])
        stats = valid_ranges[best_range]

    avg_views_str = _format_number(int(stats["avg_views"]))

    return Interpretation(
        signal=f"최적 길이: {best_range} (평균 조회수 {avg_views_str}회, {stats['count']}개 영상)",
        interpretation=f"{best_range} 길이의 영상이 가장 높은 성과를 보입니다. 이 길이에 맞춰 콘텐츠를 기획하면 좋습니다.",
        category=best_range,
        confidence="high" if stats["count"] >= 5 else "medium",
    )


# =============================================================================
# 종합 분석 함수
# =============================================================================

def get_all_rule_interpretations(
    subscriber_count: int,
    audience_data: List[AudienceData],
    geo_data: List[GeoData],
    video_stats: List[VideoStatsData],
) -> dict:
    """
    모든 규칙 기반 해석을 실행하고 결과를 반환.

    Returns:
        {
            "channel_tier": Interpretation,
            "audience": Interpretation,
            "view_consistency": Interpretation,
            "engagement": Interpretation,
        }
    """
    return {
        "channel_tier": analyze_channel_tier(subscriber_count),
        "audience": analyze_audience(audience_data, geo_data),
        "view_consistency": analyze_view_consistency(video_stats),
        "engagement": analyze_engagement(video_stats),
    }
