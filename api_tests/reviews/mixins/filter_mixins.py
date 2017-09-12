from datetime import timedelta

import pytest
from furl import furl

from osf_tests.factories import (
    AuthUserFactory,
    PreprintFactory,
    PreprintProviderFactory,
)
from reviews.permissions import GroupHelper
from reviews_tests.factories import ReviewLogFactory


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
class ReviewLogFilterMixin(object):

    @pytest.fixture()
    def url(self):
        raise NotImplementedError

    @pytest.fixture()
    def providers(self):
        return [PreprintProviderFactory(reviews_workflow='pre-moderation') for _ in range(5)]

    @pytest.fixture()
    def all_review_logs(self, providers):
        logs = []
        for p in providers:
            preprint = PreprintFactory(provider=p)
            for _ in range(5):
                logs.append(ReviewLogFactory(reviewable=preprint))
        return logs

    @pytest.fixture()
    def allowed_providers(self, providers):
        return providers

    @pytest.fixture()
    def expected_logs(self, all_review_logs, allowed_providers):
        provider_ids = set([p.id for p in allowed_providers])
        return [l for l in all_review_logs if l.reviewable.provider_id in provider_ids]

    @pytest.fixture()
    def user(self, allowed_providers):
        user = AuthUserFactory()
        for provider in allowed_providers:
            user.groups.add(GroupHelper(provider).get_group('moderator'))
        return user

    def test_filter_logs(self, app, url, user, expected_logs):
        # unfiltered
        expected = set([l._id for l in expected_logs])
        actual = get_actual(app, url, user)
        assert expected == actual

        if not expected_logs:
            return

        log = expected_logs[0]

        # filter by id
        expected = set([log._id])
        actual = get_actual(app, url, user, id=log._id)
        assert expected == actual

        # filter by action
        expected = set([l._id for l in expected_logs if l.action == log.action])
        actual = get_actual(app, url, user, action=log.action)
        assert expected == actual

        # filter by from_state
        expected = set([l._id for l in expected_logs if l.from_state == log.from_state])
        actual = get_actual(app, url, user, from_state=log.from_state)
        assert expected == actual

        # filter by to_state
        expected = set([l._id for l in expected_logs if l.to_state == log.to_state])
        actual = get_actual(app, url, user, to_state=log.to_state)
        assert expected == actual

        # filter by date_created
        expected = set([l._id for l in expected_logs])
        actual = get_actual(app, url, user, date_created=log.date_created)
        assert expected == actual

        expected = set()
        actual = get_actual(app, url, user, date_created=log.date_created - timedelta(days=1))
        assert expected == actual

        # filter by date_modified
        expected = set([l._id for l in expected_logs])
        actual = get_actual(app, url, user, date_modified=log.date_modified)
        assert expected == actual

        expected = set()
        actual = get_actual(app, url, user, date_modified=log.date_modified - timedelta(days=1))
        assert expected == actual

        # filter by reviewable
        expected = set([l._id for l in expected_logs if l.reviewable_id == log.reviewable_id])
        actual = get_actual(app, url, user, reviewable=log.reviewable._id)
        assert expected == actual

        # filter by provider
        expected = set([l._id for l in expected_logs if l.reviewable.provider_id == log.reviewable.provider_id])
        actual = get_actual(app, url, user, provider=log.reviewable.provider._id)
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
        expected = set([r._id for r in expected_reviewables if r.reviews_state == reviewable.reviews_state])
        actual = get_actual(app, url, user, reviews_state=reviewable.reviews_state)
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
        actual = get_actual(app, url, user, permissions='view_review_logs')
        assert expected == actual

        actual = get_actual(app, url, user, permissions='set_up_moderation')
        assert expected == actual

        actual = get_actual(app, url, user, permissions='set_up_moderation,view_review_logs')
        assert expected == actual

        # filter by permissions (moderator)
        user, provider = moderator_pair
        expected = set([provider._id])
        actual = get_actual(app, url, user, permissions='view_review_logs')
        assert expected == actual

        actual = get_actual(app, url, user, permissions='set_up_moderation,view_review_logs')
        assert expected == actual

        expected = set()
        actual = get_actual(app, url, user, permissions='set_up_moderation')
        assert expected == actual

        # filter by permissions (rando)
        user = AuthUserFactory()
        expected = set()
        actual = get_actual(app, url, user, permissions='view_review_logs')
        assert expected == actual

        actual = get_actual(app, url, user, permissions='set_up_moderation')
        assert expected == actual

        actual = get_actual(app, url, user, permissions='set_up_moderation,view_review_logs')
        assert expected == actual

        # filter by permissions requires auth
        res = get_actual(app, url, expect_errors=True, permissions='set_up_moderation')
        assert res.status_code == 401
