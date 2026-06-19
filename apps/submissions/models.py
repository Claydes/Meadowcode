from django.conf import settings
from django.db import models


class Language(models.TextChoices):
    PYTHON = "python", "Python"
    JAVASCRIPT = "javascript", "JavaScript"
    CPP = "cpp", "C++"


class SubmissionStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    ACCEPTED = "accepted", "Accepted"
    WRONG_ANSWER = "wrong_answer", "Wrong Answer"
    TIME_LIMIT = "time_limit", "Time Limit Exceeded"
    MEMORY_LIMIT = "memory_limit", "Memory Limit Exceeded"
    RUNTIME_ERROR = "runtime_error", "Runtime Error"
    COMPILE_ERROR = "compile_error", "Compile Error"
    INTERNAL_ERROR = "internal_error", "Internal Error"


class Submission(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    problem = models.ForeignKey(
        "problems.Problem",
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    language = models.CharField(
        max_length=32,
        choices=Language.choices,
        default=Language.PYTHON,
    )
    code = models.TextField()
    status = models.CharField(
        max_length=32,
        choices=SubmissionStatus.choices,
        default=SubmissionStatus.PENDING,
    )
    verdict_message = models.TextField(blank=True)
    runtime_ms = models.PositiveIntegerField(null=True, blank=True)
    memory_kb = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    judged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.user} -> {self.problem} ({self.status})"
