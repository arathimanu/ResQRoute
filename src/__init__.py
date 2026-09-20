"""ResQRoute: Adaptive Disaster Relief Routing.

Core modules for graph representation and shortest-path routing.
"""

from .graph import RoadGraph, RoadStatus

def dijkstra(*args, **kwargs):
    from .dijkstra import dijkstra as _dijkstra
    return _dijkstra(*args, **kwargs)

__all__ = ["RoadGraph", "RoadStatus", "dijkstra"]

