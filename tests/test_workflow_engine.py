from core.workflows.engine import WorkflowEngine, WorkflowStepExecutor
from core.workflows.models import StepResult, StepState, WorkflowDefinition, WorkflowState, WorkflowStep
from core.workflows.store import InMemoryWorkflowStore

class Executor(WorkflowStepExecutor):
    def execute(self, step, input_data, dependency_outputs):
        return StepResult(step.id, StepState.COMPLETED, output=(step.name, dependency_outputs))

def test_workflow_runs_in_dependency_order():
    a=WorkflowStep("research")
    b=WorkflowStep("write", dependency_ids=(a.id,))
    wf=WorkflowDefinition("paper", (b,a))
    run=WorkflowEngine(Executor()).run(wf)
    assert run.state is WorkflowState.COMPLETED
    assert run.outputs[b.id][1][a.id] == ("research", {})

def test_resume_skips_completed_steps():
    calls=[]
    class E(WorkflowStepExecutor):
        def execute(self, step, input_data, dependency_outputs):
            calls.append(step.name)
            return StepResult(step.id, StepState.COMPLETED, output=step.name)
    store=InMemoryWorkflowStore(); engine=WorkflowEngine(E(), store)
    a=WorkflowStep("a"); b=WorkflowStep("b", dependency_ids=(a.id,)); wf=WorkflowDefinition("wf",(a,b))
    run=engine.run(wf)
    assert calls == ["a","b"]
    resumed=engine.resume(wf, run.id)
    assert resumed.state is WorkflowState.COMPLETED
    assert calls == ["a","b"]

def test_cycle_is_rejected():
    a=WorkflowStep("a"); b=WorkflowStep("b", dependency_ids=(a.id,))
    object.__setattr__(a,"dependency_ids",(b.id,))
    try: WorkflowDefinition("cycle",(a,b)); assert False
    except ValueError: pass

def test_failed_step_persists_checkpoint():
    class E(WorkflowStepExecutor):
        def execute(self, step, input_data, dependency_outputs):
            return StepResult(step.id, StepState.FAILED, error="boom")
    wf=WorkflowDefinition("wf",(WorkflowStep("a"),))
    run=WorkflowEngine(E()).run(wf)
    assert run.state is WorkflowState.FAILED
    assert run.checkpoint.startswith("after:")
