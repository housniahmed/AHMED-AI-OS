"""Model-router-backed agent planning with strict structured output."""
from __future__ import annotations

import json
from typing import Any

from core.agent.models import AgentAction
from core.agent.runtime import AgentPlanner
from core.models.contracts import ModelRequest, ModelTask
from core.models.router import ModelRouter


class PlannerResponseError(ValueError):
    """Raised when a model response violates the planner contract."""


class ModelAgentPlanner(AgentPlanner):
    """Turn a routed model response into observations and explicit actions.

    The model is not allowed to execute anything. It may only return a JSON
    proposal. Execution remains downstream in B6/B17/B18/B33.
    """

    def __init__(self, router: ModelRouter, *, model: str | None = None) -> None:
        self.router = router
        self.model = model

    def infer(self, request: str, context: Any):
        payload = {
            "request": request,
            "context": self._context_payload(context),
            "output_contract": {
                "observations": ["string"],
                "actions": [
                    {
                        "name": "string",
                        "description": "string",
                        "level": "read|analyze|prepare|approve|execute",
                        "arguments": "object",
                    }
                ],
            },
            "rule": "Return JSON only. Propose actions; never execute them.",
        }
        response = self.router.generate(ModelRequest(
            task=ModelTask.REASONING,
            input_text=json.dumps(payload, ensure_ascii=False),
            model=self.model,
            temperature=0,
        ))
        return self._parse(response.text)

    @staticmethod
    def _parse(text: str):
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise PlannerResponseError("planner model must return valid JSON") from exc
        if not isinstance(data, dict):
            raise PlannerResponseError("planner response must be a JSON object")
        observations = data.get("observations", [])
        actions = data.get("actions", [])
        if not isinstance(observations, list) or not all(isinstance(x, str) for x in observations):
            raise PlannerResponseError("observations must be a list of strings")
        if not isinstance(actions, list):
            raise PlannerResponseError("actions must be a list")
        proposals = []
        for item in actions:
            if not isinstance(item, dict):
                raise PlannerResponseError("each action must be an object")
            for key in ("name", "description", "level"):
                if not isinstance(item.get(key), str) or not item[key].strip():
                    raise PlannerResponseError(f"action.{key} must be a non-empty string")
            arguments = item.get("arguments", {})
            if not isinstance(arguments, dict):
                raise PlannerResponseError("action.arguments must be an object")
            proposals.append(AgentAction(
                name=item["name"],
                description=item["description"],
                level=item["level"],
                arguments=arguments,
            ))
        return tuple(observations), tuple(proposals)

    @staticmethod
    def _context_payload(context: Any) -> dict[str, Any]:
        if context is None:
            return {}
        result = {}
        for field in ("knowledge", "memories", "decisions", "goals", "projects", "procedures"):
            items = getattr(context, field, ())
            result[field] = [
                {"content": getattr(item, "content", ""), "source_id": getattr(item, "source_id", "")}
                for item in items
            ]
        result["truncated"] = bool(getattr(context, "truncated", False))
        return result
