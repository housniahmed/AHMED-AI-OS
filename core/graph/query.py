"""Deterministic graph traversal primitives."""

from __future__ import annotations

from collections import deque
from uuid import UUID

from core.graph.models import GraphPath
from core.graph.store import GraphStore, InMemoryGraphStore


class GraphQuery:
    def __init__(self, store: GraphStore) -> None:
        self.store = store

    def shortest_path(self, source_id: UUID, target_id: UUID, max_depth: int = 4) -> GraphPath | None:
        if source_id == target_id:
            return GraphPath((source_id,), ())
        queue = deque([(source_id, (source_id,), ())])
        visited = {source_id}
        while queue:
            current, entities, relationships = queue.popleft()
            if len(relationships) >= max_depth:
                continue
            for edge in self._edges_from(current):
                nxt = edge.target_id if edge.source_id == current else edge.source_id
                if nxt in visited:
                    continue
                path = (entities + (nxt,), relationships + (edge.id,))
                if nxt == target_id:
                    return GraphPath(*path)
                visited.add(nxt)
                queue.append((nxt, *path))
        return None

    def _edges_from(self, entity_id: UUID):
        return [e for e in self.store.relationships.values() if e.source_id == entity_id or e.target_id == entity_id]
