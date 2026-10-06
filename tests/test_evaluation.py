from core.evaluation.models import EvaluationCase,EvaluationStatus
from core.evaluation.service import CallableMetric,DeterministicEvaluator,EvaluationFramework

def test_metric_and_summary():
    metric=CallableMetric("exact",lambda case,out:1.0 if case.expected==out else 0.0,0.8)
    fw=EvaluationFramework(DeterministicEvaluator([metric]))
    run=fw.run([EvaluationCase("ok","x","y")],lambda c:"y")
    assert run.results[0].status is EvaluationStatus.PASSED
    assert fw.summary(run)["pass_rate"]==1.0

def test_failure_and_error_are_distinguished():
    metric=CallableMetric("quality",lambda c,o:0.2,0.8); fw=EvaluationFramework(DeterministicEvaluator([metric]))
    run=fw.run([EvaluationCase("bad","x")],lambda c:"out")
    assert run.results[0].status is EvaluationStatus.FAILED
    run2=fw.run([EvaluationCase("err","x")],lambda c: (_ for _ in ()).throw(RuntimeError("boom")))
    assert run2.results[0].status is EvaluationStatus.ERROR

def test_evaluation_propagates_case_metadata():
    metric=CallableMetric("quality",lambda case,out:1.0)
    fw=EvaluationFramework(DeterministicEvaluator([metric]))
    run=fw.run(
        [EvaluationCase("model-case","x",metadata={"provider":"p","model":"m","task":"reasoning"})],
        lambda c:"ok",
    )
    assert run.results[0].metadata["provider"] == "p"
    assert run.results[0].metadata["task"] == "reasoning"
