import pytest
from django.urls import reverse

from apps.problems.models import UserProblemProgress
from tests.helpers import response_results


pytestmark = pytest.mark.django_db


def test_anonymous_problem_list_shows_only_published_unsolved_problems(
    api_client,
    problem_factory,
):
    problem_factory(slug="published", is_published=True)
    problem_factory(slug="draft", is_published=False)

    response = api_client.get(reverse("problem-list"), HTTP_HOST="localhost")

    assert response.status_code == 200
    problems = response_results(response)
    assert [problem["slug"] for problem in problems] == ["published"]
    assert problems[0]["is_solved"] is False


def test_problem_list_marks_solved_from_user_progress(
    authenticated_client,
    problem_factory,
    user,
    other_user,
):
    solved_problem = problem_factory(slug="two-sum")
    unsolved_problem = problem_factory(slug="three-sum")
    UserProblemProgress.objects.create(user=user, problem=solved_problem)
    UserProblemProgress.objects.create(user=other_user, problem=unsolved_problem)

    response = authenticated_client.get(
        reverse("problem-list"),
        HTTP_HOST="localhost",
    )

    assert response.status_code == 200
    by_slug = {problem["slug"]: problem for problem in response_results(response)}
    assert by_slug["two-sum"]["is_solved"] is True
    assert by_slug["three-sum"]["is_solved"] is False


def test_staff_can_see_unpublished_problems(api_client, problem_factory, staff_user):
    draft = problem_factory(slug="staff-only", is_published=False)
    api_client.force_authenticate(user=staff_user)

    response = api_client.get(reverse("problem-list"), HTTP_HOST="localhost")

    assert response.status_code == 200
    slugs = {problem["slug"] for problem in response_results(response)}
    assert draft.slug in slugs


def test_non_staff_user_cannot_create_problem(authenticated_client):
    response = authenticated_client.post(
        reverse("problem-list"),
        {
            "title": "Hidden Test",
            "slug": "hidden-test",
            "statement": "Solve it.",
            "function_name": "solve",
            "function_arguments": "",
            "difficulty": "easy",
            "is_published": True,
        },
        format="json",
        HTTP_HOST="localhost",
    )

    assert response.status_code == 403
