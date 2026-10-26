"""Graphviz style adapter over the renderer-neutral ÆToE cascade engine."""
from __future__ import annotations

from typing import Any, Mapping

from ..style import StyleElement, StyleSheet, load_stylesheet


def graphviz_stylesheet() -> StyleSheet:
    """Return the Graphviz source stylesheet plus its target overlays."""
    return load_stylesheet(source="GraphViz")


def resolve_graphviz_style(
    element: StyleElement | str,
    *,
    mode: str | None = None,
    target: str | None = None,
    parent: Mapping[str, Any] | None = None,
    inline: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve Graphviz attributes for the configured output target."""
    return graphviz_stylesheet().resolve(
        element, mode=mode, target=target, parent=parent, inline=inline,
    )


__all__ = ["graphviz_stylesheet", "resolve_graphviz_style"]
