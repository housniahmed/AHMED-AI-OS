from core.graph.models import Entity, EntityType, Relationship, RelationType
from core.graph.query import GraphQuery
from core.graph.store import InMemoryGraphStore


def test_graph_requires_existing_endpoints():
    store = InMemoryGraphStore()
    a = store.add_entity(Entity("Project A", EntityType.PROJECT))
    b = store.add_entity(Entity("Research", EntityType.CONCEPT))
    store.add_relationship(Relationship(a.id, b.id, RelationType.RELATED_TO, confidence=0.9))
    assert store.neighbors(a.id)[0].id == b.id


def test_shortest_path():
    store = InMemoryGraphStore()
    a = store.add_entity(Entity("A", EntityType.CONCEPT))
    b = store.add_entity(Entity("B", EntityType.CONCEPT))
    c = store.add_entity(Entity("C", EntityType.CONCEPT))
    e1 = store.add_relationship(Relationship(a.id, b.id, RelationType.RELATED_TO))
    e2 = store.add_relationship(Relationship(b.id, c.id, RelationType.SUPPORTS))
    path = GraphQuery(store).shortest_path(a.id, c.id)
    assert path is not None
    assert path.entity_ids == (a.id, b.id, c.id)
    assert path.relationship_ids == (e1.id, e2.id)
