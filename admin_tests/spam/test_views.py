from django.db import transaction
from django.test import RequestFactory
from django.http import Http404
from nose import tools as nt
from datetime import datetime, timedelta

from website.project.model import Comment

from admin.common_auth.logs import OSFLogEntry
from admin.spam.forms import ConfirmForm, EmailForm
from tests.base import AdminTestCase
from tests.factories import CommentFactory, AuthUserFactory, ProjectFactory
from admin_tests.utilities import setup_view, setup_form_view
from admin_tests.factories import UserFactory

from admin.spam.views import (
    SpamList,
    UserSpamList,
    SpamDetail,
    EmailView,
)


class TestSpamListView(AdminTestCase):
    def setUp(self):
        super(TestSpamListView, self).setUp()
        Comment.remove()
        self.project = ProjectFactory(is_public=True)
        self.user_1 = AuthUserFactory()
        self.user_2 = AuthUserFactory()
        self.project.add_contributor(self.user_1)
        self.project.add_contributor(self.user_2)
        self.project.save()
        self.user_1.save()
        self.user_2.save()
        date = datetime.utcnow()
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
        self.view = SpamList()
        self.view = setup_view(self.view, self.request, user_id=self.user_1._id)

    def test_get_spam(self):
        res = list(self.view.get_queryset())
        nt.assert_equal(len(res), 6)
        response_list = [r._id for r in res]
        should_be = [
            self.comment_6._id,
            self.comment_5._id,
            self.comment_4._id,
            self.comment_3._id,
            self.comment_2._id,
            self.comment_1._id
        ]
        nt.assert_list_equal(should_be, response_list)

    def test_get_context_data(self):
        self.view.object_list = self.view.get_queryset()
        res = self.view.get_context_data()
        nt.assert_is_instance(res['spam'], list)
        nt.assert_is_instance(res['spam'][0], dict)
        nt.assert_equal(res['status'], '1')
        nt.assert_equal(res['page_number'], 1)


class TestSpamDetail(AdminTestCase):
    def setUp(self):
        super(TestSpamDetail, self).setUp()
        self.comment = CommentFactory()
        self.comment.report_abuse(user=AuthUserFactory(), save=True,
                                  category='spam')
        self.request = RequestFactory().post('/fake_path')
        self.request.user = UserFactory()

    def test_confirm_spam(self):
        form_data = {'confirm': str(Comment.SPAM)}
        form = ConfirmForm(data=form_data)
        nt.assert_true(form.is_valid())
        view = SpamDetail()
        view = setup_form_view(
            view, self.request, form, spam_id=self.comment._id)
        with transaction.atomic():
            view.form_valid(form)
        obj = OSFLogEntry.objects.latest(field_name='action_time')
        nt.assert_equal(obj.object_id, self.comment._id)
        nt.assert_in('Confirmed SPAM:', obj.message())

    def test_confirm_ham(self):
        form_data = {'confirm': str(Comment.HAM)}
        form = ConfirmForm(data=form_data)
        nt.assert_true(form.is_valid())
        view = SpamDetail()
        view = setup_form_view(
            view, self.request, form, spam_id=self.comment._id)
        with transaction.atomic():
            view.form_valid(form)
        obj = OSFLogEntry.objects.latest(field_name='action_time')
        nt.assert_equal(obj.object_id, self.comment._id)
        nt.assert_in('Confirmed HAM:', obj.message())

    def test_form_valid_bad_id(self):
        form = ConfirmForm()
        view = SpamDetail()
        view = setup_form_view(view, self.request, form, spam_id='a1')
        with nt.assert_raises(Http404):
            view.form_valid(form)

    def test_get_context_data(self):
        view = SpamDetail()
        view = setup_view(view, self.request, spam_id=self.comment._id)
        res = view.get_context_data()
        nt.assert_equal(res['status'], '1')
        nt.assert_equal(res['page_number'], '1')
        nt.assert_is_instance(res['comment'], dict)
        nt.assert_equal(res['UNKNOWN'], Comment.UNKNOWN)
        nt.assert_equal(res['SPAM'], Comment.SPAM)
        nt.assert_equal(res['HAM'], Comment.HAM)
        nt.assert_equal(res['FLAGGED'], Comment.FLAGGED)

    def test_get_context_data_bad_id(self):
        view = setup_view(SpamDetail(), self.request, spam_id='a1')
        with nt.assert_raises(Http404):
            view.get_context_data()


class TestEmailView(AdminTestCase):
    def setUp(self):
        super(TestEmailView, self).setUp()
        self.comment = CommentFactory()
        self.comment.report_abuse(user=AuthUserFactory(), save=True,
                                  category='spam')
        self.request = RequestFactory().post('/fake_path')
        self.request.user = UserFactory()

    def test_get_object_bad_id(self):
        view = setup_view(EmailView(), self.request, spam_id='a1')
        with nt.assert_raises(Http404):
            view.get_object()


class TestUserSpamListView(AdminTestCase):
    def setUp(self):
        super(TestUserSpamListView, self).setUp()
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
        self.view = UserSpamList()
        self.view = setup_view(self.view, self.request, user_id=self.user_1._id)

    def test_get_user_spam(self):
        res = list(self.view.get_queryset())
        nt.assert_equal(len(res), 4)

    def test_get_context_data(self):
        self.view.object_list = self.view.get_queryset()
        res = self.view.get_context_data()
        nt.assert_is_instance(res['spam'], list)
        nt.assert_is_instance(res['spam'][0], dict)
        nt.assert_equal(res['status'], '1')
        nt.assert_equal(res['page_number'], 1)
        nt.assert_equal(res['user_id'], self.user_1._id)
