import pytest

from core.identity.models import UserIdentity, UserStatus
from core.identity.service import UserContextService


def test_create_and_snapshot_user_context():
    service = UserContextService()
    identity = UserIdentity(display_name="Ahmed", timezone="Africa/Casablanca", locale="fr-MA")
    service.create(identity)
    snapshot = service.snapshot(identity.user_id)
    assert snapshot.identity == identity
    assert snapshot.active_goal_ids == ()
    assert snapshot.active_project_ids == ()


def test_context_updates_are_explicit():
    service = UserContextService()
    identity = UserIdentity(display_name="Ahmed")
    service.create(identity)
    service.update_profile(identity.user_id, {"role": "engineer"})
    service.update_preferences(identity.user_id, {"language": "fr"})
    service.update_constraints(identity.user_id, {"max_daily_tasks": 5})
    snapshot = service.snapshot(identity.user_id)
    assert snapshot.profile["role"] == "engineer"
    assert snapshot.preferences["language"] == "fr"
    assert snapshot.constraints["max_daily_tasks"] == 5


def test_inactive_user_cannot_expose_context():
    service = UserContextService()
    identity = UserIdentity(display_name="Ahmed", status=UserStatus.SUSPENDED)
    with pytest.raises(PermissionError):
        service.create(identity)
