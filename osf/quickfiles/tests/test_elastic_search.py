import pytest

from osf.models import Tag
from osf.utils.testing.pytest_utils import ElasticSearchTestCase


@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
class TestQuickfilesElasticSearch(ElasticSearchTestCase):

    def test_quickfiles_files_appear_in_search(self, user):
        user.quickfolder.append_file('GreenLight.mp3')

        find = self.query_file('GreenLight.mp3')['results']

        assert len(find) == 1
        assert find[0]['node_url'] == '/{}/quickfiles/'.format(user._id)

    def test_qatest_quickfiles_files_not_appear_in_search(self, user):
        file = user.quickfolder.append_file('GreenLight.mp3')
        tag = Tag(name='qatest')
        tag.save()
        file.tags.add(tag)
        file.save()

        find = self.query_file('GreenLight.mp3')['results']

        assert len(find) == 0

    def test_quickfiles_spam_user_files_do_not_appear_in_search(self, user):
        user.disable_account()
        user.add_system_tag('spam_confirmed')
        user.save()
        user.quickfolder.append_file('GreenLight.mp3')

        find = self.query_file('GreenLight.mp3')['results']

        assert len(find) == 0
