"""Build a unified context from retrieval, structured context and graph data."""

from __future__ import annotations

from core.context.models import StructuredContext
from core.fabric.models import FabricEdge, FabricNode, UnifiedContext
from core.graph.store import GraphStore
from core.retrieval.models import RetrievalResult


class KnowledgeFabricBuilder:
    """Create one canonical context representation without losing provenance."""

    def __init__(self, graph: GraphStore, max_nodes: int = 100) -> None:
        if max_nodes < 1:
            raise ValueError("max_nodes must be >= 1")
        self.graph = graph
        self.max_nodes = max_nodes

    def build(self, retrieval: RetrievalResult, context: StructuredContext) -> UnifiedContext:
        nodes: dict = {}
        sections: dict[str, list] = {}

        for candidate in retrieval.candidates:
            node = FabricNode(
                id=candidate.id,
                kind=self._kind(candidate.metadata, candidate.source_type),
                label=candidate.source_id,
                content=candidate.content,
                source_type=candidate.source_type,
                source_id=candidate.source_id,
                relevance=candidate.fused_score,
                metadata=candidate.metadata,
            )
            nodes.setdefault(node.id, node)

        for item in context.all_items():
            node = FabricNode(
                id=self._stable_id(item.source_type, item.source_id),
                kind=item.kind,
                label=item.source_id,
                content=item.content,
                source_type=item.source_type,
                source_id=item.source_id,
                relevance=item.relevance,
                metadata=item.metadata,
            )
            nodes.setdefault(node.id, node)

        for node in list(nodes.values()):
            if node.id in getattr(self.graph, "entities", {}):
                entity = self.graph.get_entity(node.id)
                nodes[node.id] = FabricNode(
                    id=node.id, kind=entity.entity_type.value, label=entity.name,
                    content=entity.description or node.content, source_type=node.source_type,
                    source_id=node.source_id, relevance=node.relevance, metadata={**node.metadata, **entity.metadata},
                )

        ordered = sorted(nodes.values(), key=lambda n: n.relevance, reverse=True)[: self.max_nodes]
        allowed = {n.id for n in ordered}
        edges = tuple(
            FabricEdge(e.source_id, e.target_id, e.relation.value, e.confidence, e.provenance)
            for e in getattr(self.graph, "relationships", {}).values()
            if e.source_id in allowed and e.target_id in allowed
        )

        for node in ordered:
            sections.setdefault(node.kind, []).append(node.id)
        return UnifiedContext(retrieval.query.text, tuple(ordered), edges,
                              {k: tuple(v) for k, v in sections.items()},
                              truncated=len(nodes) > self.max_nodes or context.truncated)

    @staticmethod
    def _stable_id(source_type: str, source_id: str):
        from uuid import uuid5, NAMESPACE_URL
        return uuid5(NAMESPACE_URL, f"ahmed-ai-os:{source_type}:{source_id}")

    @staticmethod
    def _kind(metadata, source_type):
        return metadata.get("kind", source_type)
