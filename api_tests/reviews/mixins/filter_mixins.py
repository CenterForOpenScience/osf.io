from datetime import timedelta

import pytest
from furl import furl

from api.preprint_providers.permissions import GroupHelper
from osf_tests.factories import (
    ReviewActionFactory,
    AuthUserFactory,
    PreprintFactory,
    PreprintProviderFactory,
    ProjectFactory,
)


def get_actual(app, url, user=None, sort=None, expect_errors=False, **filters):
    url = furl(url)
    for k, v in filters.items():
        url.args['filter[{}]'.format(k)] = v
    if sort is not None:
        url.args['sort'] = sort
    url = url.url

    if expect_errors:
        if user is None:
            res = app.get(url, expect_errors=True)
        else:
            res = app.get(url, auth=user.auth, expect_errors=True)
        return res

    actual = []
    while url:
        if user is None:
            res = app.get(url)
        else:
            res = app.get(url, auth=user.auth)
        actual.extend([l['id'] for l in res.json['data']])
        url = res.json['links']['next']
    if sort is None:
        return set(actual)
    return actual


@pytest.mark.django_db
class ReviewActionFilterMixin(object):

    @pytest.fixture()
    def url(self):
        raise NotImplementedError

    @pytest.fixture()
    def providers(self):
        return [PreprintProviderFactory(reviews_workflow='pre-moderation') for _ in range(5)]

    @pytest.fixture()
    def all_actions(self, providers):
        actions = []
        for provider in providers:
            preprint = PreprintFactory(provider=provider, project=ProjectFactory(is_public=True))
            for _ in range(5):
                actions.append(ReviewActionFactory(target=preprint))
        return actions

    @pytest.fixture()
    def allowed_providers(self, providers):
        return providers

    @pytest.fixture()
    def expected_actions(self, all_actions, allowed_providers):
        provider_ids = set([p.id for p in allowed_providers])
        return [a for a in all_actions if a.target.provider_id in provider_ids]

    @pytest.fixture()
    def user(self, allowed_providers):
        user = AuthUserFactory()
        for provider in allowed_providers:
            user.groups.add(GroupHelper(provider).get_group('moderator'))
        return user

    def test_filter_actions(self, app, url, user, expected_actions):
        # unfiltered
        expected = set([l._id for l in expected_actions])
        actual = get_actual(app, url, user)
        assert expected == actual

        if not expected_actions:
            return

        action = expected_actions[0]

        # filter by id
        expected = set([action._id])
        actual = get_actual(app, url, user, id=action._id)
        assert expected == actual

        # filter by trigger
        expected = set([l._id for l in expected_actions if l.trigger == action.trigger])
        actual = get_actual(app, url, user, trigger=action.trigger)
        assert expected == actual

        # filter by from_state
        expected = set([l._id for l in expected_actions if l.from_state == action.from_state])
        actual = get_actual(app, url, user, from_state=action.from_state)
        assert expected == actual

        # filter by to_state
        expected = set([l._id for l in expected_actions if l.to_state == action.to_state])
        actual = get_actual(app, url, user, to_state=action.to_state)
        assert expected == actual

        # filter by date_created
        expected = set([l._id for l in expected_actions])
        actual = get_actual(app, url, user, date_created=action.created)
        assert expected == actual

        expected = set()
        actual = get_actual(app, url, user, date_created=action.created - timedelta(days=1))
        assert expected == actual

        # filter by date_modified
        expected = set([l._id for l in expected_actions])
        actual = get_actual(app, url, user, date_modified=action.modified)
        assert expected == actual

        expected = set()
        actual = get_actual(app, url, user, date_modified=action.modified - timedelta(days=1))
        assert expected == actual

        # filter by target
        expected = set([l._id for l in expected_actions if l.target_id == action.target_id])
        actual = get_actual(app, url, user, target=action.target._id)
        assert expected == actual

        # filter by provider
        expected = set([l._id for l in expected_actions if l.target.provider_id == action.target.provider_id])
        actual = get_actual(app, url, user, provider=action.target.provider._id)
        assert expected == actual


@pytest.mark.django_db
class ReviewableFilterMixin(object):

    @pytest.fixture()
    def url(self):
        raise NotImplementedError

    @pytest.fixture()
    def expected_reviewables(self):
        raise NotImplementedError

    @pytest.fixture()
    def user(self):
        raise NotImplementedError

    def test_reviewable_filters(self, app, url, user, expected_reviewables):
        # unfiltered
        expected = set([r._id for r in expected_reviewables])
        actual = get_actual(app, url, user)
        assert expected == actual

        if not expected_reviewables:
            return

        reviewable = expected_reviewables[0]

        # filter by reviews_state
        expected = set([r._id for r in expected_reviewables if r.machine_state == reviewable.machine_state])
        actual = get_actual(app, url, user, reviews_state=reviewable.machine_state)
        assert expected == actual

        # order by date_last_transitioned
        expected = [r._id for r in sorted(expected_reviewables, key=lambda r: r.date_last_transitioned)]
        actual = get_actual(app, url, user, sort='date_last_transitioned')
        assert expected == actual

        expected.reverse()
        actual = get_actual(app, url, user, sort='-date_last_transitioned')
        assert expected == actual


@pytest.mark.django_db
class ReviewProviderFilterMixin(object):

    @pytest.fixture()
    def url(self):
        raise NotImplementedError

    @pytest.fixture()
    def expected_providers(self):
        return [
            PreprintProviderFactory(reviews_workflow='pre-moderation'),
            PreprintProviderFactory(reviews_workflow='post-moderation'),
            PreprintProviderFactory(reviews_workflow='pre-moderation'),
            PreprintProviderFactory(reviews_workflow=None),
        ]

    @pytest.fixture()
    def moderator_pair(self, expected_providers):
        user = AuthUserFactory()
        provider = expected_providers[0]
        user.groups.add(GroupHelper(provider).get_group('moderator'))
        return (user, provider)

    @pytest.fixture()
    def admin_pair(self, expected_providers):
        user = AuthUserFactory()
        provider = expected_providers[1]
        user.groups.add(GroupHelper(provider).get_group('admin'))
        return (user, provider)

    def test_review_provider_filters(self, app, url, moderator_pair, admin_pair, expected_providers):
        # unfiltered
        expected = set([p._id for p in expected_providers])
        actual = get_actual(app, url)
        assert expected == actual

        provider = expected_providers[0]

        # filter by reviews_workflow
        expected = set([p._id for p in expected_providers if p.reviews_workflow == provider.reviews_workflow])
        actual = get_actual(app, url, reviews_workflow=provider.reviews_workflow)
        assert expected == actual

        # filter by permissions (admin)
        user, provider = admin_pair
        expected = set([provider._id])
        actual = get_actual(app, url, user, permissions='view_actions')
        assert expected == actual

        actual = get_actual(app, url, user, permissions='set_up_moderation')
        assert expected == actual

        actual = get_actual(app, url, user, permissions='set_up_moderation,view_actions')
        assert expected == actual

        # filter by permissions (moderator)
        user, provider = moderator_pair
        expected = set([provider._id])
        actual = get_actual(app, url, user, permissions='view_actions')
        assert expected == actual

        actual = get_actual(app, url, user, permissions='set_up_moderation,view_actions')
        assert expected == actual

        expected = set()
        actual = get_actual(app, url, user, permissions='set_up_moderation')
        assert expected == actual

        # filter by permissions (rando)
        user = AuthUserFactory()
        expected = set()
        actual = get_actual(app, url, user, permissions='view_actions')
        assert expected == actual

        actual = get_actual(app, url, user, permissions='set_up_moderation')
        assert expected == actual

        actual = get_actual(app, url, user, permissions='set_up_moderation,view_actions')
        assert expected == actual

        # filter by permissions requires auth
        res = get_actual(app, url, expect_errors=True, permissions='set_up_moderation')
        assert res.status_code == 401
