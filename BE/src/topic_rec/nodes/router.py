"""
Router Node - Conditional Routing Logic
"""

from src.topic_rec.state import TopicRecState


def should_retry(state: TopicRecState) -> str:
    """
    Determine if we should retry the recommendation process.

    Returns:
    - "retry": Not enough recommendations, try again
    - "done": Sufficient recommendations, proceed to end
    - "fallback": Too many retries, use fallback
    """
    recommendations = state.get("recommendations", [])
    retry_count = state.get("retry_count", 0)
    error = state.get("error")

    # If error occurred, check retry count
    if error:
        if retry_count >= 2:
            return "fallback"
        return "retry"

    # If not enough recommendations
    if len(recommendations) < 2:
        if retry_count >= 2:
            return "fallback"
        return "retry"

    return "done"


def route_by_quality(state: TopicRecState) -> str:
    """
    Route based on data quality.

    Returns:
    - "high_quality": Good data, proceed to full analysis
    - "low_quality": Poor data, skip to basic recommendation
    """
    trends = state.get("processed_trends", [])

    if not trends:
        return "low_quality"

    # Check data quality
    tech_count = sum(1 for t in trends if t.ai_category == "Technology")
    high_score_count = sum(1 for t in trends if t.trend_score > 0.1)

    # Good quality: enough tech items or high score items
    if tech_count >= 10 or high_score_count >= 5:
        return "high_quality"

    return "low_quality"
