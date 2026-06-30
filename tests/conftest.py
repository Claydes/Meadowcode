import pytest
from rest_framework.test import APIClient

from apps.problems.models import Difficulty, Problem
from apps.submissions.models import Language, Submission


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user_factory(django_user_model):
    counter = 0

    def create_user(**kwargs):
        nonlocal counter
        counter += 1
        password = kwargs.pop("password", "StrongPass123!")
        defaults = {
            "username": f"user{counter}",
            "email": f"user{counter}@example.com",
        }
        defaults.update(kwargs)
        return django_user_model.objects.create_user(password=password, **defaults)

    return create_user


@pytest.fixture
def user(user_factory):
    return user_factory(username="alice", email="alice@example.com")


@pytest.fixture
def other_user(user_factory):
    return user_factory(username="bob", email="bob@example.com")


@pytest.fixture
def staff_user(user_factory):
    return user_factory(
        username="admin",
        email="admin@example.com",
        is_staff=True,
    )


@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def problem_factory():
    counter = 0

    def create_problem(**kwargs):
        nonlocal counter
        counter += 1
        defaults = {
            "title": f"Problem {counter}",
            "slug": f"problem-{counter}",
            "statement": "Return the requested value.",
            "examples": "",
            "constraints": "",
            "function_name": "solve",
            "function_arguments": "value",
            "starter_code": "def solve(value):\n    pass\n",
            "difficulty": Difficulty.EASY,
            "is_published": True,
        }
        defaults.update(kwargs)
        return Problem.objects.create(**defaults)

    return create_problem


@pytest.fixture
def submission_factory(user_factory, problem_factory):
    def create_submission(**kwargs):
        defaults = {
            "user": user_factory(),
            "problem": problem_factory(),
            "language": Language.PYTHON,
            "code": "def solve(value):\n    return value\n",
        }
        defaults.update(kwargs)
        return Submission.objects.create(**defaults)

    return create_submission
