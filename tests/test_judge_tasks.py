import pytest

from apps.judge.services import JudgeResult
from apps.judge.tasks import run_submission
from apps.problems.models import UserProblemProgress
from apps.submissions.models import SubmissionStatus


pytestmark = pytest.mark.django_db


def test_run_submission_records_progress_for_first_accepted_submission(
    monkeypatch,
    submission_factory,
):
    submission = submission_factory(status=SubmissionStatus.PENDING)

    def fake_evaluate_submission(submission_to_judge):
        assert submission_to_judge.id == submission.id
        return JudgeResult(
            status=SubmissionStatus.ACCEPTED,
            message="Accepted",
            runtime_ms=12,
            memory_kb=256,
        )

    monkeypatch.setattr("apps.judge.tasks.evaluate_submission", fake_evaluate_submission)

    result = run_submission.run(submission.id)
    submission.refresh_from_db()

    assert result == {
        "submission_id": submission.id,
        "status": SubmissionStatus.ACCEPTED,
    }
    assert submission.status == SubmissionStatus.ACCEPTED
    assert submission.verdict_message == "Accepted"
    assert submission.runtime_ms == 12
    assert submission.memory_kb == 256
    assert submission.judged_at is not None

    progress = UserProblemProgress.objects.get(
        user=submission.user,
        problem=submission.problem,
    )
    assert progress.first_accepted_submission == submission

    second_result = run_submission.run(submission.id)
    assert second_result == {
        "submission_id": submission.id,
        "status": SubmissionStatus.ACCEPTED,
        "skipped": True,
    }
    assert UserProblemProgress.objects.filter(
        user=submission.user,
        problem=submission.problem,
    ).count() == 1


def test_run_submission_does_not_mark_wrong_answer_as_solved(
    monkeypatch,
    submission_factory,
):
    submission = submission_factory(status=SubmissionStatus.PENDING)

    monkeypatch.setattr(
        "apps.judge.tasks.evaluate_submission",
        lambda submission_to_judge: JudgeResult(
            status=SubmissionStatus.WRONG_ANSWER,
            message="Wrong answer on test #1",
        ),
    )

    run_submission.run(submission.id)

    submission.refresh_from_db()
    assert submission.status == SubmissionStatus.WRONG_ANSWER
    assert not UserProblemProgress.objects.filter(
        user=submission.user,
        problem=submission.problem,
    ).exists()


def test_run_submission_skips_non_pending_submission(
    monkeypatch,
    submission_factory,
):
    submission = submission_factory(status=SubmissionStatus.RUNNING)

    def fail_if_called(submission_to_judge):
        raise AssertionError("Judge should not run for non-pending submissions.")

    monkeypatch.setattr("apps.judge.tasks.evaluate_submission", fail_if_called)

    result = run_submission.run(submission.id)

    submission.refresh_from_db()
    assert result == {
        "submission_id": submission.id,
        "status": SubmissionStatus.RUNNING,
        "skipped": True,
    }
    assert submission.status == SubmissionStatus.RUNNING
