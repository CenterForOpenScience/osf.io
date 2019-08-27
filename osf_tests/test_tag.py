import mock
import pytest

from django.db import DataError

from framework.auth import Auth
from osf.models import Tag
from osf.exceptions import ValidationError, TagNotFoundError
from osf_tests.factories import ProjectFactory, UserFactory

pytestmark = pytest.mark.django_db

@pytest.mark.enable_implicit_clean
class TestTag:

    def test_has_an_integer_pk(self):
        tag = Tag(name='FooBar')
        tag.save()
        assert type(tag.pk) is int

    def test_uniqueness_on_name_and_system(self):
        tag = Tag(name='FooBar', system=False)
        tag.save()

        tag2 = Tag(name='FooBar', system=False)
        with pytest.raises(ValidationError):
            tag2.save()

        tag3 = Tag(name='FooBar', system=True)
        try:
            tag3.save()
        except Exception:
            pytest.fail('Saving system tag with non-unique name should not error.')

    def test_load_loads_by_name(self):
        tag_name = 'NeONDreams'
        tag = Tag(name=tag_name)
        tag.save()

        assert Tag.load(tag_name).pk == tag.pk


# copied from tests/test_models.py
class TestTags:

    @pytest.fixture()
    def project(self):
        return ProjectFactory()

    @pytest.fixture()
    def auth(self, project):
        return Auth(project.creator)

    @mock.patch('website.project.tasks.update_node_share')
    def test_add_tag(self, mock_update_share, project, auth):
        project.add_tag('scientific', auth=auth)
        assert 'scientific' in list(project.tags.values_list('name', flat=True))
        assert project.logs.latest().action == 'tag_added'
        mock_update_share.assert_called_once_with(project)

    @pytest.mark.skip('TODO: 128 is no longer max length, consider shortening')
    def test_add_tag_too_long(self, project, auth):
        with pytest.raises(ValidationError):
            project.add_tag('q' * 129, auth=auth)

    def test_add_tag_way_too_long(self, project, auth):
        with pytest.raises(DataError):
            project.add_tag('asdf' * 257, auth=auth)

    @mock.patch('website.project.tasks.update_node_share')
    def test_remove_tag(self, mock_update_share, project, auth):
        project.add_tag('scientific', auth=auth)
        mock_update_share.assert_called_once_with(project)

        project.remove_tag('scientific', auth=auth)
        assert mock_update_share.call_count == 2
        assert mock_update_share.call_args_list[1][0][0] == project

        assert 'scientific' not in list(project.tags.values_list('name', flat=True))
        assert project.logs.latest().action == 'tag_removed'

    def test_remove_tag_not_present(self, project, auth):
        with pytest.raises(TagNotFoundError):
            project.remove_tag('scientific', auth=auth)

    def test_remove_system_tag_from_user(self):
        user = UserFactory()
        system_tag = Tag.objects.create(name='test_system_tag', system=True)
        user.tags.add(system_tag)
        assert user.all_tags.first() == system_tag

        user.tags.through.objects.filter(tag=system_tag).delete()
        assert user.all_tags.count() == 0
