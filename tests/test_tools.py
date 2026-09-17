from core.domain.models import ActionLevel
from core.tools.models import ToolCall, ToolSpec
from core.tools.permissions import ToolPermissionPolicy
from core.tools.registry import ToolRegistry
from core.tools.runtime import ToolRuntime


def test_registry_discovers_registered_tools():
    registry = ToolRegistry()
    spec = ToolSpec("read_notes", "read notes", ActionLevel.READ, tags=("notes",))
    registry.register(spec)
    assert registry.get("read_notes") == spec
    assert registry.discover(tags=("notes",))[0] == spec


def test_runtime_denies_unapproved_execute():
    registry = ToolRegistry()
    registry.register(ToolSpec("send", "send message", ActionLevel.EXECUTE))
    runtime = ToolRuntime(registry, ToolPermissionPolicy({"send"}))
    runtime.bind("send", lambda args: "sent")
    result = runtime.execute(ToolCall("send"))
    assert not result.success
    assert result.error == "tool execution not authorized"


def test_runtime_executes_approved_tool():
    registry = ToolRegistry()
    registry.register(ToolSpec("send", "send message", ActionLevel.EXECUTE))
    runtime = ToolRuntime(registry, ToolPermissionPolicy({"send"}))
    runtime.bind("send", lambda args: args["text"])
    result = runtime.execute(ToolCall("send", {"text": "hello"}), approved=True)
    assert result.success
    assert result.output == "hello"
