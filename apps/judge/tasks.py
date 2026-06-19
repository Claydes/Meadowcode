from celery import shared_task
from django.utils import timezone

from .services import evaluate_submission


@shared_task(bind=True)
def run_submission(self, submission_id: int) -> dict:
    from apps.submissions.models import Submission, SubmissionStatus

    submission = Submission.objects.select_related("problem", "user").get(pk=submission_id)
    submission.status = SubmissionStatus.RUNNING
    submission.save(update_fields=("status",))

    result = evaluate_submission(submission)
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

    return {"submission_id": submission.id, "status": submission.status}
