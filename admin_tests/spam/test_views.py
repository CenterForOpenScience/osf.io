from django.test import RequestFactory
from nose import tools as nt

from tests.base import AdminTestCase
from tests.factories import CommentFactory, AuthUserFactory, ProjectFactory
from admin_tests.utilities import setup_view

from admin.spam.views import SpamList


class TestSpamListView(AdminTestCase):
    def setUp(self):
        super(TestSpamListView, self).setUp()
        self.project = ProjectFactory(is_public=True)
        self.user_1 = AuthUserFactory()
        self.user_2 = AuthUserFactory()
        self.project.add_contributor(self.user_1)
        self.project.add_contributor(self.user_2)
        self.project.save()
        self.user_1.save()
        self.user_2.save()
        self.comment_1 = CommentFactory()
