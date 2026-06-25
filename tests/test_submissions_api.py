import pytest
from django.urls import reverse

from apps.submissions.models import Language, Submission, SubmissionStatus
from tests.helpers import response_results


pytestmark = pytest.mark.django_db


def test_authenticated_user_can_create_submission_and_enqueue_judge(
    authenticated_client,
    django_capture_on_commit_callbacks,
    monkeypatch,
    problem_factory,
    user,
):
    queued_submission_ids = []

    def fake_delay(submission_id):
        queued_submission_ids.append(submission_id)

    monkeypatch.setattr("apps.submissions.views.run_submission.delay", fake_delay)
    problem = problem_factory()

    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        response = authenticated_client.post(
            reverse("submission-list"),
            {
                "problem": problem.id,
                "language": Language.PYTHON,
                "code": "def solve(value):\n    return value\n",
            },
            format="json",
            HTTP_HOST="localhost",
        )

    assert response.status_code == 201
    submission = Submission.objects.get()
    assert submission.user == user
    assert submission.problem == problem
    assert submission.status == SubmissionStatus.PENDING
    assert response.json()["status"] == SubmissionStatus.PENDING
    assert len(callbacks) == 1
    assert queued_submission_ids == [submission.id]


def test_user_cannot_submit_to_unpublished_problem(
    authenticated_client,
    django_capture_on_commit_callbacks,
    monkeypatch,
    problem_factory,
):
    queued_submission_ids = []
    monkeypatch.setattr(
        "apps.submissions.views.run_submission.delay",
        queued_submission_ids.append,
    )
    problem = problem_factory(is_published=False)

    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        response = authenticated_client.post(
            reverse("submission-list"),
            {
                "problem": problem.id,
                "language": Language.PYTHON,
                "code": "def solve(value):\n    return value\n",
            },
            format="json",
            HTTP_HOST="localhost",
        )

    assert response.status_code == 400
    assert "problem" in response.json()
    assert not Submission.objects.exists()
    assert callbacks == []
    assert queued_submission_ids == []


def test_staff_can_submit_to_unpublished_problem(
    api_client,
    django_capture_on_commit_callbacks,
    monkeypatch,
    problem_factory,
    staff_user,
):
    queued_submission_ids = []
    monkeypatch.setattr(
        "apps.submissions.views.run_submission.delay",
        queued_submission_ids.append,
    )
    problem = problem_factory(is_published=False)
    api_client.force_authenticate(user=staff_user)

    with django_capture_on_commit_callbacks(execute=True):
        response = api_client.post(
            reverse("submission-list"),
            {
                "problem": problem.id,
                "language": Language.PYTHON,
                "code": "def solve(value):\n    return value\n",
            },
            format="json",
            HTTP_HOST="localhost",
        )

    assert response.status_code == 201
    assert Submission.objects.get().problem == problem
    assert queued_submission_ids == [response.json()["id"]]


def test_unsupported_language_is_rejected_before_submission_is_queued(
    authenticated_client,
    django_capture_on_commit_callbacks,
    monkeypatch,
    problem_factory,
):
    queued_submission_ids = []
    monkeypatch.setattr(
        "apps.submissions.views.run_submission.delay",
        queued_submission_ids.append,
    )
    problem = problem_factory()

    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        response = authenticated_client.post(
            reverse("submission-list"),
            {
                "problem": problem.id,
                "language": Language.JAVASCRIPT,
                "code": "function solve(value) { return value; }",
            },
            format="json",
            HTTP_HOST="localhost",
        )

    assert response.status_code == 400
    assert "language" in response.json()
    assert not Submission.objects.exists()
    assert callbacks == []
    assert queued_submission_ids == []


def test_anonymous_user_cannot_create_submission(api_client, problem_factory):
    problem = problem_factory()

    response = api_client.post(
        reverse("submission-list"),
        {
            "problem": problem.id,
            "language": Language.PYTHON,
            "code": "def solve(value):\n    return value\n",
        },
        format="json",
        HTTP_HOST="localhost",
    )

    assert response.status_code in {401, 403}


def test_user_submission_list_is_limited_to_own_submissions(
    api_client,
    submission_factory,
    user,
    other_user,
    staff_user,
):
    own_submission = submission_factory(user=user)
    other_submission = submission_factory(user=other_user)

    api_client.force_authenticate(user=user)
    response = api_client.get(reverse("submission-list"), HTTP_HOST="localhost")
    assert response.status_code == 200
    assert [item["id"] for item in response_results(response)] == [own_submission.id]

    api_client.force_authenticate(user=staff_user)
    response = api_client.get(reverse("submission-list"), HTTP_HOST="localhost")
    assert response.status_code == 200
    returned_ids = {item["id"] for item in response_results(response)}
    assert returned_ids == {own_submission.id, other_submission.id}
