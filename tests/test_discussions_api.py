import pytest
from django.urls import reverse

from apps.discussions.models import DiscussionComment, DiscussionThread
from tests.helpers import response_results


pytestmark = pytest.mark.django_db


def test_authenticated_user_can_create_thread_and_comment(
    authenticated_client,
    problem_factory,
    user,
):
    problem = problem_factory()

    thread_response = authenticated_client.post(
        reverse("discussion-thread-list"),
        {
            "problem": problem.id,
            "title": "How should this be solved?",
            "body": "I am thinking about a hash map.",
        },
        format="json",
        HTTP_HOST="localhost",
    )

    assert thread_response.status_code == 201
    thread = DiscussionThread.objects.get()
    assert thread.user == user
    assert thread.problem == problem

    comment_response = authenticated_client.post(
        reverse("discussion-comment-list"),
        {
            "thread": thread.id,
            "body": "That works in linear time.",
        },
        format="json",
        HTTP_HOST="localhost",
    )

    assert comment_response.status_code == 201
    comment = DiscussionComment.objects.get()
    assert comment.user == user
    assert comment.thread == thread

    detail_response = authenticated_client.get(
        reverse("discussion-thread-detail", kwargs={"pk": thread.id}),
        HTTP_HOST="localhost",
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["comments_count"] == 1


def test_discussion_threads_are_filtered_by_problem(api_client, problem_factory, user):
    requested_problem = problem_factory(slug="requested")
    other_problem = problem_factory(slug="other")
    requested_thread = DiscussionThread.objects.create(
        user=user,
        problem=requested_problem,
        title="Requested",
        body="Shown",
    )
    DiscussionThread.objects.create(
        user=user,
        problem=other_problem,
        title="Other",
        body="Hidden",
    )

    response = api_client.get(
        reverse("discussion-thread-list"),
        {"problem": requested_problem.id},
        HTTP_HOST="localhost",
    )

    assert response.status_code == 200
    assert [thread["id"] for thread in response_results(response)] == [
        requested_thread.id
    ]


def test_anonymous_users_cannot_see_threads_for_unpublished_problems(
    api_client,
    problem_factory,
    user,
):
    published_problem = problem_factory(slug="visible", is_published=True)
    unpublished_problem = problem_factory(slug="hidden", is_published=False)
    visible_thread = DiscussionThread.objects.create(
        user=user,
        problem=published_problem,
        title="Visible",
        body="Shown",
    )
    DiscussionThread.objects.create(
        user=user,
        problem=unpublished_problem,
        title="Hidden",
        body="Hidden",
    )

    response = api_client.get(
        reverse("discussion-thread-list"),
        HTTP_HOST="localhost",
    )

    assert response.status_code == 200
    assert [thread["id"] for thread in response_results(response)] == [
        visible_thread.id
    ]


def test_user_cannot_create_thread_for_unpublished_problem(
    authenticated_client,
    problem_factory,
):
    problem = problem_factory(is_published=False)

    response = authenticated_client.post(
        reverse("discussion-thread-list"),
        {
            "problem": problem.id,
            "title": "Hidden topic",
            "body": "Should not be public.",
        },
        format="json",
        HTTP_HOST="localhost",
    )

    assert response.status_code == 400
    assert "problem" in response.json()
    assert not DiscussionThread.objects.exists()


def test_user_cannot_comment_on_thread_for_unpublished_problem(
    authenticated_client,
    problem_factory,
    other_user,
):
    thread = DiscussionThread.objects.create(
        user=other_user,
        problem=problem_factory(is_published=False),
        title="Hidden topic",
        body="Hidden body",
    )

    response = authenticated_client.post(
        reverse("discussion-comment-list"),
        {
            "thread": thread.id,
            "body": "I should not see this.",
        },
        format="json",
        HTTP_HOST="localhost",
    )

    assert response.status_code == 400
    assert "thread" in response.json()
    assert not DiscussionComment.objects.exists()


def test_staff_can_see_threads_for_unpublished_problems(
    api_client,
    problem_factory,
    staff_user,
):
    thread = DiscussionThread.objects.create(
        user=staff_user,
        problem=problem_factory(is_published=False),
        title="Staff only",
        body="Draft discussion",
    )
    api_client.force_authenticate(user=staff_user)

    response = api_client.get(
        reverse("discussion-thread-list"),
        HTTP_HOST="localhost",
    )

    assert response.status_code == 200
    assert [item["id"] for item in response_results(response)] == [thread.id]


def test_only_thread_owner_or_staff_can_update_thread(
    api_client,
    problem_factory,
    user,
    other_user,
    staff_user,
):
    thread = DiscussionThread.objects.create(
        user=user,
        problem=problem_factory(),
        title="Original",
        body="Original body",
    )
    url = reverse("discussion-thread-detail", kwargs={"pk": thread.id})

    api_client.force_authenticate(user=other_user)
    response = api_client.patch(
        url,
        {"title": "Nope"},
        format="json",
        HTTP_HOST="localhost",
    )
    assert response.status_code == 403

    api_client.force_authenticate(user=staff_user)
    response = api_client.patch(
        url,
        {"title": "Moderated"},
        format="json",
        HTTP_HOST="localhost",
    )
    assert response.status_code == 200
    thread.refresh_from_db()
    assert thread.title == "Moderated"
