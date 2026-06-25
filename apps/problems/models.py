from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models


class Difficulty(models.TextChoices):
    EASY = "easy", "Easy"
    MEDIUM = "medium", "Medium"
    HARD = "hard", "Hard"


class Tag(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=100, unique=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class Problem(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="authored_problems",
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="problems")
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    statement = models.TextField()
    examples = models.TextField(blank=True)
    constraints = models.TextField(blank=True)
    function_name = models.CharField(
        max_length=100,
        default="solve",
        validators=[
            RegexValidator(
                regex=r"^[A-Za-z_][A-Za-z0-9_]*$",
                message="Function name must be a valid Python identifier.",
            )
        ],
    )
    function_arguments = models.CharField(
        max_length=255,
        blank=True,
        validators=[
            RegexValidator(
                regex=r"^$|^[A-Za-z_][A-Za-z0-9_]*(,\s*[A-Za-z_][A-Za-z0-9_]*)*$",
                message="Arguments must be comma-separated Python identifiers.",
            )
        ],
    )
    starter_code = models.TextField(blank=True)
    difficulty = models.CharField(
        max_length=16,
        choices=Difficulty.choices,
        default=Difficulty.EASY,
    )
    time_limit_ms = models.PositiveIntegerField(default=1000)
    memory_limit_mb = models.PositiveIntegerField(default=256)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("id",)

    def __str__(self) -> str:
        return self.title


class UserProblemProgress(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="problem_progress",
    )
    problem = models.ForeignKey(
        Problem,
        on_delete=models.CASCADE,
        related_name="user_progress",
    )
    first_accepted_submission = models.ForeignKey(
        "submissions.Submission",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="first_accept_progress",
    )
    solved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-solved_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("user", "problem"),
                name="unique_user_problem_progress",
            )
        ]

    def __str__(self) -> str:
        return f"{self.user} solved {self.problem}"


class TestCase(models.Model):
    problem = models.ForeignKey(
        Problem,
        on_delete=models.CASCADE,
        related_name="test_cases",
    )
    input_data = models.TextField()
    expected_output = models.TextField()
    is_sample = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("order", "id")

    def __str__(self) -> str:
        return f"{self.problem}: test #{self.pk}"
