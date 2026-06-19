from dataclasses import dataclass


@dataclass(frozen=True)
class JudgeResult:
    status: str
    message: str
    runtime_ms: int | None = None
    memory_kb: int | None = None


def evaluate_submission(submission) -> JudgeResult:
    return JudgeResult(
        status="accepted",
        message="Judge pipeline placeholder. Sandbox execution is not implemented yet.",
        runtime_ms=0,
        memory_kb=0,
    )
