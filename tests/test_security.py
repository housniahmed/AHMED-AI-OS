from uuid import uuid4
from core.security.models import AccessLevel,SecurityAction,SecurityPrincipal
from core.security.service import SecurityService,InMemorySecurityAuditSink

def test_deny_by_default_and_explicit_grant():
    sink=InMemorySecurityAuditSink(); service=SecurityService(sink); user=SecurityPrincipal(uuid4()); action=SecurityAction("calendar","create",AccessLevel.WRITE)
    assert service.authorize(user,action).allowed is False
    service.grant(user.user_id,"calendar",AccessLevel.WRITE)
    assert service.authorize(user,action).allowed is True
    assert len(sink.decisions)==2

def test_least_privilege_and_revoke():
    service=SecurityService(); user=SecurityPrincipal(uuid4()); action=SecurityAction("tools","run",AccessLevel.EXECUTE)
    service.grant(user.user_id,"tools",AccessLevel.READ); assert not service.authorize(user,action).allowed
    service.grant(user.user_id,"tools",AccessLevel.EXECUTE); assert service.authorize(user,action).allowed
    service.revoke(user.user_id,"tools"); assert not service.authorize(user,action).allowed
