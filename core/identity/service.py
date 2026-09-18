"""Deterministic identity and context service."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from core.identity.models import UserContextRecord, UserContextSnapshot, UserIdentity, UserStatus


class UserContextService:
    def __init__(self) -> None:
        self._records: dict[UUID, UserContextRecord] = {}

    def create(self, identity: UserIdentity) -> UserContextRecord:
        if identity.user_id in self._records:
            raise ValueError(f"user already exists: {identity.user_id}")
        self._validate_identity(identity)
        if identity.status != UserStatus.ACTIVE:
            raise PermissionError("only active users can be created")
        record = UserContextRecord(identity=identity)
        self._records[identity.user_id] = record
        return record

    def get(self, user_id: UUID) -> UserContextRecord | None:
        return self._records.get(user_id)

    def snapshot(self, user_id: UUID) -> UserContextSnapshot:
        record = self._records.get(user_id)
        if record is None:
            raise KeyError(f"unknown user: {user_id}")
        if record.identity.status != UserStatus.ACTIVE:
            raise PermissionError("user context is not active")
        return record.snapshot()

    def update_profile(self, user_id: UUID, values: dict) -> UserContextSnapshot:
        record = self._require_active(user_id)
        record.profile.update(values)
        record.updated_at = datetime.now(timezone.utc)
        return record.snapshot()

    def update_preferences(self, user_id: UUID, values: dict) -> UserContextSnapshot:
        record = self._require_active(user_id)
        record.preferences.update(values)
        record.updated_at = datetime.now(timezone.utc)
        return record.snapshot()

    def update_constraints(self, user_id: UUID, values: dict) -> UserContextSnapshot:
        record = self._require_active(user_id)
        record.constraints.update(values)
        record.updated_at = datetime.now(timezone.utc)
        return record.snapshot()

    def set_active_goals(self, user_id: UUID, goal_ids: list[UUID]) -> UserContextSnapshot:
        record = self._require_active(user_id)
        record.active_goal_ids = list(dict.fromkeys(goal_ids))
        record.updated_at = datetime.now(timezone.utc)
        return record.snapshot()

    def set_active_projects(self, user_id: UUID, project_ids: list[UUID]) -> UserContextSnapshot:
        record = self._require_active(user_id)
        record.active_project_ids = list(dict.fromkeys(project_ids))
        record.updated_at = datetime.now(timezone.utc)
        return record.snapshot()

    def _require_active(self, user_id: UUID) -> UserContextRecord:
        record = self._records.get(user_id)
        if record is None:
            raise KeyError(f"unknown user: {user_id}")
        if record.identity.status != UserStatus.ACTIVE:
            raise PermissionError("user context is not active")
        return record

    @staticmethod
    def _validate_identity(identity: UserIdentity) -> None:
        if not identity.display_name.strip() and not identity.email:
            raise ValueError("identity requires display_name or email")
        if not identity.timezone.strip():
            raise ValueError("timezone cannot be empty")
        if not identity.locale.strip():
            raise ValueError("locale cannot be empty")
