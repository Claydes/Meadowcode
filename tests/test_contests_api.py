import pytest
from django.urls import reverse

from apps.contests.models import ContestRegistration
from tests.helpers import response_results


pytestmark = pytest.mark.django_db


def test_contest_list_shows_only_public_contests_to_anonymous_users(
    api_client,
    contest_factory,
):
    public_contest = contest_factory(slug="weekly-1", is_public=True)
    contest_factory(slug="private-round", is_public=False)

    response = api_client.get(reverse("contest-list"), HTTP_HOST="localhost")

    assert response.status_code == 200
    assert [contest["slug"] for contest in response_results(response)] == [
        public_contest.slug
    ]


def test_staff_can_see_private_contests(api_client, contest_factory, staff_user):
    private_contest = contest_factory(slug="private-round", is_public=False)
    api_client.force_authenticate(user=staff_user)

    response = api_client.get(reverse("contest-list"), HTTP_HOST="localhost")

    assert response.status_code == 200
    slugs = {contest["slug"] for contest in response_results(response)}
    assert private_contest.slug in slugs


def test_authenticated_user_can_join_contest_once(
    authenticated_client,
    contest_factory,
    user,
):
    contest = contest_factory(slug="weekly-join")
    url = reverse("contest-join", kwargs={"slug": contest.slug})

    first_response = authenticated_client.post(url, HTTP_HOST="localhost")
    second_response = authenticated_client.post(url, HTTP_HOST="localhost")

    assert first_response.status_code == 201
    assert second_response.status_code == 200
    assert first_response.json()["contest"] == contest.slug
    assert ContestRegistration.objects.filter(contest=contest, user=user).count() == 1
