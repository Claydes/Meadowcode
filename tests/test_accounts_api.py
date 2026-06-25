import pytest
from django.urls import reverse

from apps.problems.models import UserProblemProgress
from apps.submissions.models import SubmissionStatus


pytestmark = pytest.mark.django_db


def test_registration_requires_email(api_client, django_user_model):
    response = api_client.post(
        reverse("account-register"),
        {
            "username": "neo",
            "password": "StrongPass123!",
        },
        format="json",
        HTTP_HOST="localhost",
    )

    assert response.status_code == 400
    assert "email" in response.json()
    assert not django_user_model.objects.filter(username="neo").exists()


def test_registration_creates_user_with_required_email(api_client, django_user_model):
    response = api_client.post(
        reverse("account-register"),
        {
            "username": "trinity",
            "email": "trinity@example.com",
            "password": "StrongPass123!",
        },
        format="json",
        HTTP_HOST="localhost",
    )

    assert response.status_code == 201
    assert response.json()["email"] == "trinity@example.com"
    assert "password" not in response.json()

    user = django_user_model.objects.get(username="trinity")
    assert user.email == "trinity@example.com"
    assert user.check_password("StrongPass123!")


def test_me_reports_solved_count_from_progress_table(
    authenticated_client,
    problem_factory,
    submission_factory,
    user,
):
    solved_problem = problem_factory(slug="solved-problem")
    accepted_without_progress = problem_factory(slug="accepted-without-progress")

    UserProblemProgress.objects.create(user=user, problem=solved_problem)
    submission_factory(
        user=user,
        problem=accepted_without_progress,
        status=SubmissionStatus.ACCEPTED,
    )

    response = authenticated_client.get(
        reverse("account-me"),
        HTTP_HOST="localhost",
    )

    assert response.status_code == 200
    assert response.json()["solved_count"] == 1
