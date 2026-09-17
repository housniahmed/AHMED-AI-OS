from core.context.models import ContextItem, StructuredContext
from core.fabric.builder import KnowledgeFabricBuilder
from core.graph.models import Entity, EntityType, Relationship, RelationType
from core.graph.store import InMemoryGraphStore
from core.retrieval.models import RetrievalCandidate, RetrievalQuery, RetrievalResult
from uuid import uuid4


def test_fabric_unifies_retrieval_and_graph():
    graph = InMemoryGraphStore()
    a = graph.add_entity(Entity("Project", EntityType.PROJECT))
    b = graph.add_entity(Entity("Goal", EntityType.GOAL))
    edge = graph.add_relationship(Relationship(a.id, b.id, RelationType.HAS_GOAL, confidence=.9))
    candidate = RetrievalCandidate(a.id, "project context", "project", "p1", "internal", fused_score=1.0)
    retrieval = RetrievalResult(RetrievalQuery("project"), (candidate,))
    item = ContextItem("project context", "project", "project", "p1", 1.0, "internal")
    context = StructuredContext("project", projects=(item,))
    fabric = KnowledgeFabricBuilder(graph).build(retrieval, context)
    assert fabric.query == "project"
    assert fabric.nodes[0].id == a.id
    assert any(e.source_id == a.id and e.target_id == b.id for e in fabric.edges)


def test_fabric_respects_node_budget():
    graph = InMemoryGraphStore()
    candidates = tuple(RetrievalCandidate(uuid4(), f"c{i}", "document", str(i), "internal", fused_score=i) for i in range(3))
    result = KnowledgeFabricBuilder(graph, max_nodes=2).build(
        RetrievalResult(RetrievalQuery("x"), candidates), StructuredContext("x")
    )
    assert len(result.nodes) == 2
    assert result.truncated
