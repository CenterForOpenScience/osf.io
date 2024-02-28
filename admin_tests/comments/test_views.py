from django.test import RequestFactory
from django.utils import timezone
from datetime import timedelta

from osf.models import Comment

from tests.base import AdminTestCase
from osf_tests.factories import AuthUserFactory, ProjectFactory
from osf_tests.factories import CommentFactory
from admin_tests.utilities import setup_view

from admin.comments.views import (
    CommentList,
    UserCommentList,
)


class TestSpamListView(AdminTestCase):
    def setUp(self):
        super().setUp()
        Comment.objects.all().delete()
        self.project = ProjectFactory(is_public=True)
        self.user_1 = AuthUserFactory()
        self.user_2 = AuthUserFactory()
        self.project.add_contributor(self.user_1)
        self.project.add_contributor(self.user_2)
        self.project.save()
        self.user_1.save()
        self.user_2.save()
        date = timezone.now()
        self.comment_1 = CommentFactory(node=self.project, user=self.user_1)
        self.comment_2 = CommentFactory(node=self.project, user=self.user_1)
        self.comment_3 = CommentFactory(node=self.project, user=self.user_1)
        self.comment_4 = CommentFactory(node=self.project, user=self.user_1)
        self.comment_5 = CommentFactory(node=self.project, user=self.user_2)
        self.comment_6 = CommentFactory(node=self.project, user=self.user_2)
        self.comment_1.report_abuse(
            user=self.user_2,
            save=True,
            category='spam',
            date=date - timedelta(seconds=5)
        )
        self.comment_2.report_abuse(
            user=self.user_2,
            save=True,
            category='spam',
            date=date - timedelta(seconds=4)
        )
        self.comment_3.report_abuse(
            user=self.user_2,
            save=True,
            category='spam',
            date=date - timedelta(seconds=3)
        )
        self.comment_4.report_abuse(
            user=self.user_2,
            save=True,
            category='spam',
            date=date - timedelta(seconds=2)
        )
        self.comment_5.report_abuse(
            user=self.user_1,
            save=True,
            category='spam',
            date=date - timedelta(seconds=1)
        )
        self.comment_6.report_abuse(user=self.user_1, save=True,
                                    category='spam')
        self.request = RequestFactory().get('/fake_path')
        self.view = CommentList()
        self.view = setup_view(self.view, self.request, user_id=self.user_1._id)

    def test_get_spam(self):
        res = list(self.view.get_queryset())
        assert len(res) == 6
        response_list = [r._id for r in res]
        should_be = [
            self.comment_6._id,
            self.comment_5._id,
            self.comment_4._id,
            self.comment_3._id,
            self.comment_2._id,
            self.comment_1._id
        ]
        assert set(should_be) == set(response_list)


class TestUserCommentListView(AdminTestCase):
    def setUp(self):
        super().setUp()
        self.project = ProjectFactory(is_public=True)
        self.user_1 = AuthUserFactory()
        self.user_2 = AuthUserFactory()
        self.project.add_contributor(self.user_1)
        self.project.add_contributor(self.user_2)
        self.project.save()
        self.user_1.save()
        self.user_2.save()
        self.comment_1 = CommentFactory(node=self.project, user=self.user_1)
        self.comment_2 = CommentFactory(node=self.project, user=self.user_1)
        self.comment_3 = CommentFactory(node=self.project, user=self.user_1)
        self.comment_4 = CommentFactory(node=self.project, user=self.user_1)
        self.comment_5 = CommentFactory(node=self.project, user=self.user_2)
        self.comment_6 = CommentFactory(node=self.project, user=self.user_2)
        self.comment_1.report_abuse(user=self.user_2, save=True,
                                    category='spam')
        self.comment_2.report_abuse(user=self.user_2, save=True,
                                    category='spam')
        self.comment_3.report_abuse(user=self.user_2, save=True,
                                    category='spam')
        self.comment_4.report_abuse(user=self.user_2, save=True,
                                    category='spam')
        self.comment_5.report_abuse(user=self.user_1, save=True,
                                    category='spam')
        self.comment_6.report_abuse(user=self.user_1, save=True,
                                    category='spam')
        self.request = RequestFactory().get('/fake_path')
        self.view = UserCommentList()
        self.view = setup_view(self.view, self.request, user_guid=self.user_1._id)

    def test_get_user_spam(self):
        res = list(self.view.get_queryset())
        assert len(res) == 4
