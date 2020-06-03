from datetime import timedelta

import pytest
from furl import furl

from osf_tests.factories import (
    ReviewActionFactory,
    AuthUserFactory,
    PreprintFactory,
    PreprintProviderFactory,
    ProjectFactory,
)
from osf.utils import permissions


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
class ReviewActionFilterMixin:

    @pytest.fixture()
    def url(self):
        raise NotImplementedError

    @pytest.fixture()
    def provider(self):
        return PreprintProviderFactory(reviews_workflow='pre-moderation')

    @pytest.fixture()
    def provider2(self):
        return PreprintProviderFactory(reviews_workflow='pre-moderation')

    @pytest.fixture()
    def action(self, provider):
        preprint = PreprintFactory(
            provider=provider,
            project=ProjectFactory(is_public=True)
        )
        action = ReviewActionFactory(
            target=preprint,
            trigger='submit',
            from_state='edit_comment',
            to_state='withdrawn'
        )
        return action

    @pytest.fixture()
    def action2(self, provider2):
        preprint = PreprintFactory(
            provider=provider2,
            project=ProjectFactory(is_public=True)
        )
        action = ReviewActionFactory(
            target=preprint,
            trigger='reject',
            from_state='initial',
            to_state='accepted'
        )
        return action

    @pytest.fixture()
    def user(self, provider, provider2):
        user = AuthUserFactory()
        user.groups.add(provider.get_group('moderator'))
        user.groups.add(provider2.get_group('moderator'))
        return user

    def test_filter_actions(self, app, url, user, action, action2):
        resp = app.get(url, auth=user.auth)
        assert resp.status_code == 200
        data = resp.json['data']
        assert len(data) == 2
        action_data = {item['id'] for item in data}
        assert action_data == {action._id, action2._id}

        # filter by id
        resp = app.get(f'{url}?filter[id]={action._id}', auth=user.auth)
        assert resp.status_code == 200
        data = resp.json['data']
        assert len(data) == 1
        action_data = {item['id'] for item in data}
        assert action_data == {action._id}

        # filter by trigger
        resp = app.get(f'{url}?filter[trigger]={action.trigger}', auth=user.auth)
        assert resp.status_code == 200
        data = resp.json['data']
        assert len(data) == 1
        action_data = {item['id'] for item in data}
        assert action_data == {action._id}

        # filter by from_state
        resp = app.get(f'{url}?filter[from_state]={action2.from_state}', auth=user.auth)
        assert resp.status_code == 200
        data = resp.json['data']
        assert len(data) == 1
        action_data = {item['id'] for item in data}
        assert action_data == {action2._id}

        # filter by to_state
        resp = app.get(f'{url}?filter[to_state]={action2.to_state}', auth=user.auth)
        assert resp.status_code == 200
        data = resp.json['data']
        assert len(data) == 1
        action_data = {item['id'] for item in data}
        assert action_data == {action2._id}

        # filter by date_created
        resp = app.get(f'{url}?filter[date_created]={action.created}', auth=user.auth)
        assert resp.status_code == 200
        data = resp.json['data']
        assert len(data) == 2
        action_data = {item['id'] for item in data}
        assert action_data == {action._id, action2._id}

        expected = set()
        actual = get_actual(
            app, url, user,
            date_created=action.created - timedelta(days=1))
        assert expected == actual

        # filter by date_modified
        resp = app.get(f'{url}?filter[date_modified]={action.modified}', auth=user.auth)
        assert resp.status_code == 200
        data = resp.json['data']
        assert len(data) == 2
        action_data = {item['id'] for item in data}
        assert action_data == {action._id, action2._id}

        expected = set()
        actual = get_actual(
            app, url, user,
            date_modified=action.modified - timedelta(days=1))
        assert expected == actual

        # filter by target
        resp = app.get(f'{url}?filter[target]={action2.target._id}', auth=user.auth)
        assert resp.status_code == 200
        data = resp.json['data']
        assert len(data) == 1
        action_data = {item['id'] for item in data}
        assert action_data == {action2._id}

        # filter by provider
        resp = app.get(f'{url}?filter[provider]={action2.target.provider._id}', auth=user.auth)
        assert resp.status_code == 200
        data = resp.json['data']
        assert len(data) == 1
        action_data = {item['id'] for item in data}
        assert action_data == {action2._id}

    def test_no_permission(self, app, url, action):
        res = app.get(url, expect_errors=True)
        assert res.status_code == 401

        some_rando = AuthUserFactory()
        res = app.get(url, auth=some_rando.auth)
        assert not res.json['data']


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
        expected = set(
            [r._id for r in expected_reviewables if r.machine_state == reviewable.machine_state])
        actual = get_actual(
            app, url, user, reviews_state=reviewable.machine_state)
        assert expected == actual

        # order by date_last_transitioned
        expected = [
            r._id for r in sorted(
                expected_reviewables,
                key=lambda r: r.date_last_transitioned)]
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
        user.groups.add(provider.get_group('moderator'))
        return (user, provider)

    @pytest.fixture()
    def admin_pair(self, expected_providers):
        user = AuthUserFactory()
        provider = expected_providers[1]
        user.groups.add(provider.get_group(permissions.ADMIN))
        return (user, provider)

    def test_review_provider_filters(
            self, app, url, moderator_pair, admin_pair, expected_providers):
        # unfiltered
        expected = set([p._id for p in expected_providers])
        actual = get_actual(app, url)
        assert expected == actual

        provider = expected_providers[0]

        # filter by reviews_workflow
        expected = set(
            [p._id for p in expected_providers if p.reviews_workflow == provider.reviews_workflow])
        actual = get_actual(
            app, url, reviews_workflow=provider.reviews_workflow)
        assert expected == actual

        # filter by permissions (admin)
        user, provider = admin_pair
        expected = set([provider._id])
        actual = get_actual(app, url, user, permissions='view_actions')
        assert expected == actual

        actual = get_actual(app, url, user, permissions='set_up_moderation')
        assert expected == actual

        actual = get_actual(
            app, url, user, permissions='set_up_moderation,view_actions')
        assert expected == actual

        # filter by permissions (moderator)
        user, provider = moderator_pair
        expected = set([provider._id])
        actual = get_actual(app, url, user, permissions='view_actions')
        assert expected == actual

        actual = get_actual(
            app, url, user, permissions='set_up_moderation,view_actions')
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

        actual = get_actual(
            app, url, user, permissions='set_up_moderation,view_actions')
        assert expected == actual

        # filter by permissions requires auth
        res = get_actual(
            app, url, expect_errors=True,
            permissions='set_up_moderation')
        assert res.status_code == 401
