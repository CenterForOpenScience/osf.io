import pytest

from osf_tests.factories import (
    ReviewActionFactory,
    AuthUserFactory,
    PreprintFactory,
    PreprintProviderFactory,
    ProjectFactory,
)
from api.base.settings.defaults import API_BASE


@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
class TestReviewActionFilters():

    @pytest.fixture()
    def url(self):
        return f'/{API_BASE}actions/reviews/'

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

        # filter by date_modified
        resp = app.get(f'{url}?filter[date_modified]={action.modified}', auth=user.auth)
        assert resp.status_code == 200
        data = resp.json['data']
        assert len(data) == 2
        action_data = {item['id'] for item in data}
        assert action_data == {action._id, action2._id}

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
