"""Persistent memory access and bounded, owner-scoped lexical retrieval."""
from uuid import UUID
from core.persistence.postgres import PostgresMemoryRepository
from core.retrieval.models import RetrievalCandidate
from core.retrieval.security import sensitivity_rank

class PersistentMemoryService:
    def __init__(self,database,owner_id):
        self.database=database
        self.owner_id=UUID(str(owner_id))

    def save(self,memory):
        with self.database.transaction(self.owner_id) as conn:
            repo=PostgresMemoryRepository(conn,self.owner_id)
            repo.save(memory)
            return repo.get(memory.id)

    def get(self,memory_id):
        with self.database.transaction(self.owner_id) as conn:
            return PostgresMemoryRepository(conn,self.owner_id).get(memory_id)

    def list_by_type(self,memory_type):
        with self.database.transaction(self.owner_id) as conn:
            return PostgresMemoryRepository(conn,self.owner_id).list_by_type(memory_type)

class PostgresMemoryRetriever:
    def __init__(self,service):
        self.service=service

    def search(self,query):
        if query.user_id != self.service.owner_id:
            return []
        # Conservative model-context ceiling; confidential/restricted stay out.
        ceiling=min(sensitivity_rank(query.sensitivity_max),1)
        allowed=["public","internal"][:ceiling+1]
        with self.service.database.transaction(self.service.owner_id) as conn, conn.cursor() as cur:
            cur.execute("""SELECT id,memory_type,content,sensitivity,confidence,
                valid_from,valid_until,tags,metadata,source_type,source_id,
                source_locator,source_excerpt,captured_at,created_at,updated_at
                FROM memories WHERE user_context_id=%s AND sensitivity=ANY(%s)
                AND (valid_from IS NULL OR valid_from<=now())
                AND (valid_until IS NULL OR valid_until>now())
                AND (cardinality(%s::text[])=0 OR memory_type=ANY(%s::text[]))
                AND (%s::text IS NULL OR metadata->>'project_id'=%s)
                AND to_tsvector('simple',content) @@ plainto_tsquery('simple',%s)
                ORDER BY ts_rank(to_tsvector('simple',content),plainto_tsquery('simple',%s)) DESC,id
                LIMIT %s""",(self.service.owner_id,allowed,list(query.memory_types),list(query.memory_types),
                str(query.project_id) if query.project_id else None,str(query.project_id) if query.project_id else None,
                query.text,query.text,min(query.top_k,100)))
            repo=PostgresMemoryRepository(conn,self.service.owner_id)
            memories=[repo._decode(row) for row in cur.fetchall()]
        return [RetrievalCandidate(m.id,m.content,m.provenance.source_type,m.provenance.source_id,
            m.sensitivity.value,lexical_score=1.0/(i+1),metadata={"kind":"memory","user_id":str(self.service.owner_id),
            "user_context_id":str(self.service.owner_id),"memory_type":m.memory_type.value,
            "captured_at":m.provenance.captured_at.isoformat(),"source_locator":m.provenance.locator})
            for i,m in enumerate(memories)]
