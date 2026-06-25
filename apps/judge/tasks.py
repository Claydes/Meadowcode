from celery import shared_task
from django.db import transaction
from django.utils import timezone

from .services import JudgeResult, evaluate_submission


@shared_task(bind=True)
def run_submission(self, submission_id: int) -> dict:
    from apps.submissions.models import Submission, SubmissionStatus

    with transaction.atomic():
        submission = (
            Submission.objects.select_for_update()
            .select_related("problem", "user")
            .get(pk=submission_id)
        )
        if submission.status != SubmissionStatus.PENDING:
            return {
                "submission_id": submission.id,
                "status": submission.status,
                "skipped": True,
            }
        submission.status = SubmissionStatus.RUNNING
        submission.save(update_fields=("status",))

    try:
        result = evaluate_submission(submission)
    except Exception as exc:
        result = JudgeResult(
            status=SubmissionStatus.INTERNAL_ERROR,
            message=f"Judge failed unexpectedly: {exc}",
        )
    with transaction.atomic():
        submission = (
            Submission.objects.select_for_update()
            .select_related("problem", "user")
            .get(pk=submission_id)
        )
        if submission.status != SubmissionStatus.RUNNING:
            return {
                "submission_id": submission.id,
                "status": submission.status,
                "skipped": True,
            }

        submission.status = result.status
        submission.verdict_message = result.message
        submission.runtime_ms = result.runtime_ms
        submission.memory_kb = result.memory_kb
        submission.judged_at = timezone.now()
        submission.save(
            update_fields=(
                "status",
                "verdict_message",
                "runtime_ms",
                "memory_kb",
                "judged_at",
            )
        )

        if submission.status == SubmissionStatus.ACCEPTED:
            from apps.problems.models import UserProblemProgress

            UserProblemProgress.objects.get_or_create(
                user=submission.user,
                problem=submission.problem,
                defaults={"first_accepted_submission": submission},
            )

    return {"submission_id": submission.id, "status": submission.status}
