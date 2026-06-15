"""Assemble and run the LangGraph restoration state machine.

    START -> analyze -> restore -> verify -> finalize -> END
                          ^___________|  (bounded retry when verify fails)
"""

from __future__ import annotations

from functools import partial

from langgraph.graph import END, START, StateGraph

from photo_repair.config import Settings, get_settings
from photo_repair.image_client import ImageClient
from photo_repair.nodes import (
    analyze_node,
    finalize_node,
    plan_node,
    restore_node,
    route_after_verify,
    verify_node,
)
from photo_repair.state import RestorationState


def build_graph(client: ImageClient, max_attempts: int = 2, base_dir: str = "restored_photos"):
    """Compile the restoration graph, binding the client and run options to the nodes."""
    graph = StateGraph(RestorationState)

    graph.add_node("analyze", partial(analyze_node, client=client))
    graph.add_node("plan", partial(plan_node, client=client))
    graph.add_node("restore", partial(restore_node, client=client))
    graph.add_node("verify", partial(verify_node, client=client))
    graph.add_node("finalize", partial(finalize_node, base_dir=base_dir))

    graph.add_edge(START, "analyze")
    graph.add_edge("analyze", "plan")
    graph.add_edge("plan", "restore")
    graph.add_edge("restore", "verify")
    graph.add_conditional_edges(
        "verify",
        partial(route_after_verify, max_attempts=max_attempts),
        {"restore": "restore", "finalize": "finalize"},
    )
    graph.add_edge("finalize", END)

    return graph.compile()


def restore_photo(
    image_bytes: bytes,
    input_path: str,
    client: ImageClient,
    mime_type: str = "image/png",
    max_attempts: int = 2,
    base_dir: str = "restored_photos",
) -> RestorationState:
    """Run the full pipeline on one image and return the final state."""
    graph = build_graph(client, max_attempts=max_attempts, base_dir=base_dir)
    initial = RestorationState(
        input_path=input_path, image_bytes=image_bytes, mime_type=mime_type
    )
    result = graph.invoke(initial)
    # LangGraph returns the final state values (dict-like); normalise to RestorationState.
    if isinstance(result, RestorationState):
        return result
    return RestorationState.model_validate(dict(result))


def restore_photo_from_settings(
    image_bytes: bytes,
    input_path: str,
    mime_type: str = "image/png",
    settings: Settings | None = None,
) -> RestorationState:
    """Convenience wrapper that builds the client from settings."""
    settings = settings or get_settings()
    client = ImageClient.from_settings(settings)
    return restore_photo(
        image_bytes=image_bytes,
        input_path=input_path,
        client=client,
        mime_type=mime_type,
        max_attempts=settings.max_restore_attempts,
        base_dir=settings.output_dir,
    )
