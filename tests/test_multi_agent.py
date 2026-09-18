from core.agents.models import AgentExecutionState, AgentResult, AgentRole, AgentTask, MultiAgentPlan
from core.agents.system import AgentSelector, AgentWorker, MultiAgentSystem

class Worker(AgentWorker):
    def run(self, task, dependency_results):
        return AgentResult(task.id, AgentExecutionState.COMPLETED, output=(task.description, len(dependency_results)))

class Selector(AgentSelector):
    def select(self, task):
        return Worker()

def test_dependency_order_and_outputs():
    first = AgentTask("research", AgentRole.RESEARCH)
    second = AgentTask("analyze", AgentRole.ANALYST, dependency_ids=(first.id,))
    results = MultiAgentSystem(Selector()).execute(MultiAgentPlan((second, first)))
    assert [r.state for r in results] == [AgentExecutionState.COMPLETED, AgentExecutionState.COMPLETED]
    assert results[1].output[1] == 1

def test_cycle_is_rejected():
    a = AgentTask("a")
    b = AgentTask("b", dependency_ids=(a.id,))
    object.__setattr__(a, "dependency_ids", (b.id,))
    plan = MultiAgentPlan((a, b))
    try:
        plan.topological_order()
        assert False
    except ValueError:
        pass

def test_failed_dependency_blocks_downstream():
    class FailingWorker(AgentWorker):
        def run(self, task, dependency_results):
            if task.description == "first":
                return AgentResult(task.id, AgentExecutionState.FAILED, error="failure")
            return AgentResult(task.id, AgentExecutionState.COMPLETED)
    class S(AgentSelector):
        def select(self, task): return FailingWorker()
    first = AgentTask("first")
    second = AgentTask("second", dependency_ids=(first.id,))
    results = MultiAgentSystem(S()).execute(MultiAgentPlan((first, second)))
    assert results[0].state is AgentExecutionState.FAILED
    assert results[1].state is AgentExecutionState.BLOCKED
