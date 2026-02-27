"""
Topic Recommendation Engine - LangGraph Definition

This module defines the LangGraph workflow for topic recommendation.

Flow:
    source_select -> collect -> process -> cluster -> analyze -> recommend -> [validate]
                                                                                |
                                                                        done / retry
"""

from langgraph.graph import StateGraph, END

from src.topic_rec.state import TopicRecState
from src.topic_rec.nodes import (
    collect_node,
    process_node,
    cluster_node,
    analyze_node,
    recommend_node,
    should_retry,
)
from src.topic_rec.agents.source_selector import source_select_node


def create_topic_rec_graph() -> StateGraph:
    """
    Create the Topic Recommendation LangGraph.

    Returns:
        Compiled StateGraph ready for execution
    """
    graph = StateGraph(TopicRecState)

    # Add nodes
    graph.add_node("source_select", source_select_node)
    graph.add_node("collect", collect_node)
    graph.add_node("process", process_node)
    graph.add_node("cluster", cluster_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("recommend", recommend_node)

    # Add edges
    graph.add_edge("source_select", "collect")
    graph.add_edge("collect", "process")
    graph.add_edge("process", "cluster")
    graph.add_edge("cluster", "analyze")
    graph.add_edge("analyze", "recommend")

    # Conditional edge after recommend
    graph.add_conditional_edges(
        "recommend",
        should_retry,
        {
            "done": END,
            "retry": "collect",
            "fallback": END,
        }
    )

    # Set entry point
    graph.set_entry_point("source_select")

    return graph.compile()


# Pre-compiled graph instance
topic_rec_graph = create_topic_rec_graph()


if __name__ == "__main__":
    initial_state = {
        "persona": {
            "channel_name": "테스트 채널",
            "one_liner": "AI/개발 기술을 쉽게 설명하는 채널",
            "main_topics": ["AI", "프로그래밍", "개발 도구"],
            "target_audience": "주니어 개발자",
            "hit_patterns": ["신기술 리뷰", "비교 분석"],
            "current_viewer_needs": ["AI 도구 사용법", "커리어 조언"],
            "growth_opportunities": ["로봇공학", "양자컴퓨팅"],
            "tone_manner": "친근하고 쉬운 설명",
            "trend_focus": True,
        },
        "trends": [],
        "processed_trends": [],
        "category_clusters": [],
        "clusters": [],
        "insights": {},
        "recommendations": [],
        "source_config": None,
        "retry_count": 0,
        "error": None,
        "current_step": "init",
    }

    final_state = topic_rec_graph.invoke(initial_state)

    recommendations = final_state.get("recommendations", [])
    print("\n" + "=" * 60)
    print("RECOMMENDATIONS")
    print("=" * 60)
    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            label = rec.get("recommendation_type_label", "")
            print(f"\n[{i}] [{label}] {rec.get('title', 'N/A')}")
            print(f"    Layer: {rec.get('source_layer', 'N/A')}")
            print(f"    Topic: {rec.get('based_on_topic', 'N/A')}")
            print(f"    Direction: {rec.get('recommendation_direction', 'N/A')}")
            print(f"    Urgency: {rec.get('urgency', 'normal')}")
    else:
        print("\nNo recommendations generated.")
    print("=" * 60)
