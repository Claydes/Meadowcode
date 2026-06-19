from django.conf import settings
from django.db import models
from django.utils import timezone


class Contest(models.Model):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_contests",
    )
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="ContestRegistration",
        related_name="contests",
        blank=True,
    )
    problems = models.ManyToManyField(
        "problems.Problem",
        through="ContestProblem",
        related_name="contests",
        blank=True,
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("starts_at",)

    @property
    def is_active(self) -> bool:
        now = timezone.now()
        return self.starts_at <= now <= self.ends_at

    def __str__(self) -> str:
        return self.title


class ContestProblem(models.Model):
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE)
    problem = models.ForeignKey("problems.Problem", on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)
    points = models.PositiveIntegerField(default=100)

    class Meta:
        ordering = ("order", "id")
        unique_together = ("contest", "problem")

    def __str__(self) -> str:
        return f"{self.contest}: {self.problem}"


class ContestRegistration(models.Model):
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("contest", "user")
        ordering = ("-joined_at",)

    def __str__(self) -> str:
        return f"{self.user} in {self.contest}"
