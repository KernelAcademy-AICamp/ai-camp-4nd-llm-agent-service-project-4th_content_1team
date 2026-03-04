"""
Topic Recommendation Engine

LangGraph-based workflow for recommending YouTube video topics
based on current trends from multiple sources.

Usage:
    from src.topic_rec import topic_rec_graph

    result = topic_rec_graph.invoke(initial_state)
    recommendations = result["recommendations"]
"""

from src.topic_rec.graph import (
    topic_rec_graph,
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

__all__ = [
    # Graph
    "topic_rec_graph",
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
]
