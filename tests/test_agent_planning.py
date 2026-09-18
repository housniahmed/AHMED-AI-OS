from core.agents.models import AgentRole
from core.agents.planning import AgentPlanningEngine, DecompositionRequest, StaticTaskDecomposer, TaskProposal

def test_decomposition_builds_explicit_dag():
    d = StaticTaskDecomposer((TaskProposal("research", AgentRole.RESEARCH), TaskProposal("analyze", AgentRole.ANALYST, (0,), 4), TaskProposal("review", AgentRole.REVIEWER, (1,))))
    result = AgentPlanningEngine(d).create_plan(DecompositionRequest("Prepare paper"))
    ordered = result.plan.topological_order()
    assert [t.description for t in ordered] == ["research", "analyze", "review"]
    assert ordered[1].metadata["priority"] == 4

def test_empty_decomposition_rejected():
    try:
        AgentPlanningEngine(StaticTaskDecomposer(())).create_plan(DecompositionRequest("Goal")); assert False
    except ValueError: pass

def test_max_tasks_enforced():
    try:
        AgentPlanningEngine(StaticTaskDecomposer((TaskProposal("a"), TaskProposal("b")))).create_plan(DecompositionRequest("Goal", max_tasks=1)); assert False
    except ValueError: pass

def test_invalid_dependency_index_rejected():
    try:
        AgentPlanningEngine(StaticTaskDecomposer((TaskProposal("a", dependency_indexes=(2,)),))).create_plan(DecompositionRequest("Goal")); assert False
    except ValueError: pass
