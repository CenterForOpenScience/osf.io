import mock
from django.db import transaction
from django.test import RequestFactory
from nose import tools as nt
from datetime import datetime, timedelta

from admin.common_auth.logs import OSFLogEntry
from admin.spam.forms import ConfirmForm
from tests.base import AdminTestCase
from tests.factories import CommentFactory, AuthUserFactory, ProjectFactory
from admin_tests.utilities import setup_view, setup_form_view
from admin_tests.factories import UserFactory

from admin.spam.views import SpamList, UserSpamList, SpamDetail


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
        self.view.object_list = self.view.get_query_set()
        res = self.view.get_context_data()



class TestSpamDetail(AdminTestCase):
    def setUp(self):
        super(TestSpamDetail, self).setUp()
        self.comment = CommentFactory()
        self.request = RequestFactory().post('/fake_path')
        self.request.user = UserFactory()

    @mock.patch('admin.spam.views.SpamDetail.success_url')
    def test_add_log(self, mock_success_url):
        form_data = {'confirm': '2'}
        form = ConfirmForm(data=form_data)
        nt.assert_true(form.is_valid())
        view = SpamDetail()
        view = setup_form_view(
            view, self.request, form, spam_id=self.comment._id)
        with transaction.atomic():
            view.form_valid(form)
        obj = OSFLogEntry.objects.latest(field_name='action_time')
        nt.assert_equal(obj.object_id, self.comment._id)

    def test_confirm_ham(self):
        pass

    def test_get_context_data(self):
        pass


class TestEmailFormView(AdminTestCase):
    def setUp(self):
        super(TestEmailFormView, self).setUp()

    def test_get_context(self):
        pass

    def test_get_initial(self):
        pass

    @mock.patch('admin.spam.views.send_mail')
    def test_form_valid(self, mock_mail):
        pass


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

    def test_get_user_spam(self):
        guid = self.user_1._id
        request = RequestFactory().get('/fake_path')
        view = UserSpamList()
        view = setup_view(view, request, user_id=guid)
        res = list(view.get_queryset())
        nt.assert_equal(len(res), 4)

    def test_get_context_data(self):
        pass
