"""Persist each turn before returning; never replay incomplete turns automatically."""
from uuid import uuid4
from core.conversation.models import Conversation, ConversationStatus, Message, MessageRole, ConversationReply

class PostgresConversationService:
    def __init__(self, database, owner_id, provider=None):
        self.database=database
        self.owner_id=owner_id
        self._provider=provider

    def create(self,user_id,title="New conversation"):
        if user_id!=self.owner_id:
            raise PermissionError("wrong owner")
        if not title.strip():
            raise ValueError("Conversation title must not be empty.")
        cid=uuid4()
        with self.database.transaction(self.owner_id) as conn, conn.cursor() as cur:
            cur.execute("INSERT INTO conversations(id,owner_id,title) VALUES (%s,%s,%s)",(cid,user_id,title.strip()))
        return self.get(cid)

    def get(self,conversation_id):
        with self.database.transaction(self.owner_id) as conn, conn.cursor() as cur:
            cur.execute("SELECT title,status,created_at,updated_at FROM conversations WHERE id=%s AND owner_id=%s",(conversation_id,self.owner_id))
            row=cur.fetchone()
            if row is None:
                raise KeyError("Conversation not found.")
            cur.execute("SELECT id,role,content,created_at FROM conversation_messages WHERE conversation_id=%s AND owner_id=%s ORDER BY seq",(conversation_id,self.owner_id))
            messages=[Message(MessageRole(role),content,id=mid,created_at=at) for mid,role,content,at in cur.fetchall()]
        return Conversation(self.owner_id,row[0],id=conversation_id,status=ConversationStatus(row[1]),messages=messages,created_at=row[2],updated_at=row[3])

    def history(self,conversation_id):
        return self.get(conversation_id).messages

    def _append(self,cid,msg):
        with self.database.transaction(self.owner_id) as conn, conn.cursor() as cur:
            cur.execute("UPDATE conversations SET updated_at=clock_timestamp() WHERE id=%s AND owner_id=%s AND status='active' RETURNING id",(cid,self.owner_id))
            if cur.fetchone() is None:
                raise KeyError("Active conversation not found.")
            cur.execute("INSERT INTO conversation_messages(id,conversation_id,owner_id,role,content,created_at) VALUES (%s,%s,%s,%s,%s,%s)",(msg.id,cid,self.owner_id,msg.role.value,msg.content,msg.created_at))

    def send(self,conversation_id,user_message):
        msg=Message(MessageRole.USER,user_message)
        self._append(conversation_id,msg)
        if self._provider is None:
            return ConversationReply(conversation_id,msg,False,"accepted_pending_provider")
        reply=Message(MessageRole.ASSISTANT,self._provider.respond(self.get(conversation_id),msg))
        self._append(conversation_id,reply)
        return ConversationReply(conversation_id,reply,True,"completed")
