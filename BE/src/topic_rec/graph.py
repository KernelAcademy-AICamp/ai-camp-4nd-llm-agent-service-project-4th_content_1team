"""
Topic Recommendation Engine - LangGraph Definition

This module defines the LangGraph workflow for topic recommendation.

Flow:
    collect -> process -> cluster -> analyze -> recommend -> [validate]
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
from src.topic_rec.nodes.recommender import PERSONA_PRESETS


def create_topic_rec_graph() -> StateGraph:
    """
    Create the Topic Recommendation LangGraph.

    Returns:
        Compiled StateGraph ready for execution
    """
    # Initialize graph with state schema
    graph = StateGraph(TopicRecState)

    # Add nodes
    graph.add_node("collect", collect_node)
    graph.add_node("process", process_node)
    graph.add_node("cluster", cluster_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("recommend", recommend_node)

    # Add edges (linear flow)
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
    graph.set_entry_point("collect")

    return graph.compile()


# Pre-compiled graph instance
topic_rec_graph = create_topic_rec_graph()


def run_topic_recommendation(persona_key: str = "tech_kr") -> dict:
    """
    Run the topic recommendation workflow.

    Args:
        persona_key: Key from PERSONA_PRESETS (tech_kr, finance_kr, general_kr)

    Returns:
        Final state with recommendations
    """
    persona = PERSONA_PRESETS.get(persona_key, PERSONA_PRESETS["tech_kr"])

    initial_state = {
        "persona": persona,
        "trends": [],
        "processed_trends": [],
        "category_clusters": [],  # 계층 구조 클러스터
        "clusters": [],           # 기존 호환용 클러스터
        "insights": {},
        "recommendations": [],
        "retry_count": 0,
        "error": None,
        "current_step": "init",
    }

    print("=" * 60)
    print(f"Topic Recommendation Engine")
    print(f"Channel: {persona.get('channel_name', 'Unknown')}")
    print(f"Categories: {persona.get('preferred_categories', ['All'])}")
    print("=" * 60)

    # Run the graph
    final_state = topic_rec_graph.invoke(initial_state)

    # Print summary
    print("\n" + "=" * 60)
    print("RECOMMENDATIONS")
    print("=" * 60)

    recommendations = final_state.get("recommendations", [])
    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            print(f"\n[{i}] {rec.get('title', 'N/A')}")
            print(f"    Topic: {rec.get('based_on_topic', 'N/A')}")
            print(f"    Why hot: {rec.get('trend_basis', 'N/A')}")
            print(f"    Urgency: {rec.get('urgency', 'normal')}")
    else:
        print("\nNo recommendations generated.")

    print("\n" + "=" * 60)

    return final_state


# CLI entry point
if __name__ == "__main__":
    import sys

    persona = sys.argv[1] if len(sys.argv) > 1 else "tech_kr"
    run_topic_recommendation(persona)
