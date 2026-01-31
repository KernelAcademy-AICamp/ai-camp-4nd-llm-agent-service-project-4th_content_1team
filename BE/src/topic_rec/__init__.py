"""
Topic Recommendation Engine

LangGraph-based workflow for recommending YouTube video topics
based on current trends from multiple sources.

Usage:
    from src.topic_rec import run_topic_recommendation

    result = run_topic_recommendation("tech_kr")
    recommendations = result["recommendations"]
"""

from src.topic_rec.graph import (
    topic_rec_graph,
    run_topic_recommendation,
    create_topic_rec_graph,
)
from src.topic_rec.state import (
    TopicRecState,
    TrendItem,
    TopicCluster,
    Recommendation,
    CategoryCluster,
    SubCategoryCluster,
    TrendTopic,
)
from src.topic_rec.nodes.recommender import PERSONA_PRESETS

__all__ = [
    # Graph
    "topic_rec_graph",
    "run_topic_recommendation",
    "create_topic_rec_graph",
    # State
    "TopicRecState",
    "TrendItem",
    "TopicCluster",
    "Recommendation",
    # Hierarchical Types
    "CategoryCluster",
    "SubCategoryCluster",
    "TrendTopic",
    # Presets
    "PERSONA_PRESETS",
]
