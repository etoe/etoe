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


def atom_graph_default_nodesep_and_ranksep ():
    return ['0.03', '0.015']


def atom_graph_level_nodesep_and_ranksep(level):
    if level == 0:
        rs = '0.025'
        ns = '0.3'
    elif level == 1:
        rs = '0.025'
        ns = '0.3'
    elif level == 2:
        rs = '0.05'
        ns = '0.25'
    elif level == 3:
        rs = '0.075'
        ns = '0.2'
    elif level == 4:
        rs = '0.1'
        ns = '0.17'
    elif level == 5:
        rs = '0.2'
        ns = '0.14'
    elif level == 6:
        rs = '0.3'
        ns = '0.11'
    elif level == 7:
        rs = '0.6'
        ns = '0.09'
    elif level == 8:
        rs = '0.7'
        ns = '0.08'
    else:
        rs = '0.7'
        ns = '0.08'
    return [ns,rs]


def atom_graph_filtered_level_nodesep_and_ranksep(level):
    if level == 0:
        rs = '0.025'
        ns = '0.3'
    elif level == 1:
        rs = '0.025'
        ns = '0.3'
    elif level == 2:
        rs = '0.05'
        ns = '0.25'
    elif level == 3:
        rs = '0.075'
        ns = '0.2'
    elif level == 4:
        rs = '0.1'
        ns = '0.17'
    elif level == 5:
        rs = '0.125'
        ns = '0.14'
    elif level == 6:
        rs = '0.15'
        ns = '0.11'
    elif level == 7:
        rs = '0.175'
        ns = '0.09'
    elif level == 8:
        rs = '0.20'
        ns = '0.08'
    else:
        rs = '0.225'
        ns = '0.08'
    return [ns,rs]


def atom_graph_node_default_fontsize ():
    return 11


def atom_graph_node_default_width_and_height ():
    return [0.23, 0.24]


def atom_graph_node_width_of_depth(depth, map = False):
    d = depth
    if map or d <= 3:
        w = 0.2
    elif d <= 4:
        w = 0.15
    elif d <= 5:
        w = 0.10
    elif d <= 6:
        w = 0.05
    elif d <= 7:
        w = 0.04
    elif d <= 8:
        w = 0.03
    else:
        w = 0.02
    return w


def atom_graph_node_width_and_height(depth, label, map = False):
    l = len(label)
    if l >= 10:
        width = 0.75
    elif l >= 9:
        width = 0.70
    elif l >= 8:
        width = 0.65
    elif l >= 7:
        width = 0.60
    elif l >= 6:
        width = 0.55
    elif l >= 5:
        width = 0.45
    elif l >= 4:
        width = 0.35
    elif l >= 3:
        width = 0.30
    elif l >= 2:
        width = 0.25
    elif l >= 1:
        width = 0.2
    else:
        width = atom_graph_node_width_of_depth(depth, map)
    w = 0
    h = 0        
    if l < 11:
        w = width
    if l == 0:
        h = width
    return [w, h]


__all__ = ["graphviz_stylesheet", "resolve_graphviz_style", 
           "atom_graph_default_nodesep_and_ranksep",
           "atom_graph_level_nodesep_and_ranksep", 
           "atom_graph_filtered_level_nodesep_and_ranksep",
           "atom_graph_node_default_fontsize"
           "atom_graph_node_default_width_and_height", 
           "atom_graph_node_width_of_depth", 
           "atom_graph_node_width_and_height"]
