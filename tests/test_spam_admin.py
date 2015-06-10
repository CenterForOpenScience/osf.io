from __future__ import absolute_import
from nose.tools import *  # noqa PEP8 asserts


from framework.auth import Auth
from website.project.model import Comment
import website.settings

from tests.base import (
    OsfTestCase,
)
from tests.factories import (
    ProjectFactory, AuthUserFactory
)
from framework.exceptions import HTTPError
from website.spam_admin.spam_admin_settings import SPAM_ASSASSIN_URL,SPAM_ASSASSIN_TEACHING_URL
import httpretty
from website.spam_admin.utils import train_spam, project_is_spam
from website.project.model import Node
from website.project.views.node import project_before_set_public
import json

class TestCommentSpamAdmin(OsfTestCase):
    # Note: Comments behave differently when spam assassin is active versus when it is inactive
    # thus there are multiple tests that are repeated with a single configuration difference
    # but expecting different results

    def setUp(self):
        super(TestCommentSpamAdmin, self).setUp()
        self.project = ProjectFactory(is_public=True)
        self.project.save()

        #spam assassin
        self.GTUBE = "SPAM"

        self.spam_admin = AuthUserFactory(spam_admin=True)

    def _configure_project(self, project, comment_level):

        project.comment_level = comment_level
        project.save()

    def _add_comment(self, project, content=None, **kwargs):
        def request_callback(request, uri, headers):
            if self.GTUBE in request.body:
                return (200, headers, json.dumps({"decision":"SPAM"}))
            return (200, headers, json.dumps({"decision":"HAM"}))

        httpretty.register_uri(
            httpretty.POST, SPAM_ASSASSIN_URL,
            body=request_callback
        )

        content = content if content is not None else 'hammer to fall'
        url = project.api_url + 'comment/'
        ret = self.app.post_json(
            url,
            {
                'content': content,
                'isPublic': 'public',
                'page': 'node',
                'target': project._id
            },
            **kwargs
        )

        return Comment.load(ret.json['comment']['id'])

    ########################## TEST MODEL / UTIL FUNCTIONS  #####################################################
    @httpretty.activate
    def test_comment_added_is_spam_with_spam_assassin_active(self):
        website.settings.SPAM_ASSASSIN = True
        comment = self._add_comment(
            self.project, content = self.GTUBE, auth=self.project.creator.auth,
        )
        self.project.reload()

        assert_equal(len(self.project.commented), 1)
        assert_equal(comment.spam_status, Comment.POSSIBLE_SPAM)

    @httpretty.activate
    def test_comment_added_is_spam_with_spam_assassin_inactive(self):
        website.settings.SPAM_ASSASSIN = False
        comment = self._add_comment(
            self.project, content = self.GTUBE, auth=self.project.creator.auth,
        )
        self.project.reload()

        assert_equal(len(self.project.commented), 1)
        assert_equal(comment.spam_status, Comment.UNKNOWN)

    @httpretty.activate
    def test_comment_added_is_not_spam_with_spam_assassin_active(self):
        website.settings.SPAM_ASSASSIN = True
        comment = self._add_comment(
            self.project,auth=self.project.creator.auth,
        )
        self.project.reload()

        assert_equal(len(self.project.commented), 1)
        assert_equal(comment.spam_status , Comment.UNKNOWN)

    @httpretty.activate
    def test_comment_added_is_not_spam_with_spam_assassin_inactive(self):
        website.settings.SPAM_ASSASSIN = False
        comment = self._add_comment(
            self.project,auth=self.project.creator.auth,
        )
        self.project.reload()

        assert_equal(len(self.project.commented), 1)
        assert_equal(comment.spam_status , Comment.UNKNOWN)

    @httpretty.activate
    def test_train_spam_comment_with_spam_assasin_active(self):
        website.settings.SPAM_ASSASSIN = True
        httpretty.register_uri(
            httpretty.POST, SPAM_ASSASSIN_TEACHING_URL,
            body=lambda r, u, h: (200, h,json.dumps({"status":"Learned"}))
        )

        comment = self._add_comment(
            self.project,
            content=self.GTUBE,
            auth=self.project.creator.auth,
        )
        self.project.reload()

        assert_true(train_spam(comment, is_spam=True))

    @httpretty.activate
    def test_train_spam_comment_with_spam_assasin_inactive(self):
        website.settings.SPAM_ASSASSIN = False
        httpretty.register_uri(
            httpretty.POST, SPAM_ASSASSIN_TEACHING_URL,
            body=lambda r, u, h: (200, h,json.dumps({"status":"Learned"}))
        )

        comment = self._add_comment(
            self.project,
            content=self.GTUBE,
            auth=self.project.creator.auth,
        )
        self.project.reload()

        assert_false(train_spam(comment, is_spam=True))

    @httpretty.activate
    def test_train_ham_comment_with_spam_assassin_active(self):
        website.settings.SPAM_ASSASSIN = True
        httpretty.register_uri(
            httpretty.POST, SPAM_ASSASSIN_TEACHING_URL,
            body=lambda r,u,h: (200,h,json.dumps({"status":"Learned"}))
        )
        comment = self._add_comment(
            self.project, auth=self.project.creator.auth,
        )

        assert_true(train_spam(comment, is_spam=False))

    @httpretty.activate
    def test_train_ham_comment_with_spam_assassin_inactive(self):
        website.settings.SPAM_ASSASSIN = False
        httpretty.register_uri(
            httpretty.POST, SPAM_ASSASSIN_TEACHING_URL,
            body=lambda r,u,h: (200,h,json.dumps({"status":"Learned"}))
        )
        comment = self._add_comment(
            self.project, auth=self.project.creator.auth,
        )

        assert_false(train_spam(comment, is_spam=False))

    @httpretty.activate
    def test_auto_mark_spam_if_flagged_enough_times(self):
        comment = self._add_comment(
            self.project, auth=self.project.creator.auth,
        )

        Comment.NUM_FLAGS_FOR_SPAM = 10

        for i in range(Comment.NUM_FLAGS_FOR_SPAM):
            reporter = AuthUserFactory()
            url = self.project.api_url + 'comment/{0}/report/'.format(comment._id)
            self.app.post_json(
                url,
                {
                    'category': 'spam',
                    'text': 'ads',
                },
                auth=reporter.auth,
            )

        comment.reload()
        assert_equal(comment.spam_status , Comment.POSSIBLE_SPAM)

    @httpretty.activate
    def test_dont_auto_mark_spam_if_not_flagged_enough_times(self):
        comment = self._add_comment(
            self.project, auth=self.project.creator.auth,
        )

        Comment.NUM_FLAGS_FOR_SPAM = 10

        for i in range(Comment.NUM_FLAGS_FOR_SPAM-1):
            reporter = AuthUserFactory()
            url = self.project.api_url + 'comment/{0}/report/'.format(comment._id)
            self.app.post_json(
                url,
                {
                    'category': 'spam',
                    'text': 'ads',
                },
                auth=reporter.auth,
            )

        comment.reload()
        assert_equal(comment.spam_status , Comment.UNKNOWN)

    @httpretty.activate
    def test_auto_mark_spam_if_flagged_enough_times_num_flags_is_one(self):
        comment = self._add_comment(
            self.project, auth=self.project.creator.auth,
        )

        Comment.NUM_FLAGS_FOR_SPAM = 1

        for i in range(Comment.NUM_FLAGS_FOR_SPAM):
            reporter = AuthUserFactory()
            url = self.project.api_url + 'comment/{0}/report/'.format(comment._id)
            self.app.post_json(
                url,
                {
                    'category': 'spam',
                    'text': 'ads',
                },
                auth=reporter.auth,
            )

        comment.reload()
        assert_equal(comment.spam_status , Comment.POSSIBLE_SPAM)

    @httpretty.activate
    def test_dont_auto_mark_spam_if_not_flagged_enough_times_num_flags_is_one(self):
        comment = self._add_comment(
            self.project, auth=self.project.creator.auth,
        )

        Comment.NUM_FLAGS_FOR_SPAM = 1

        for i in range(Comment.NUM_FLAGS_FOR_SPAM-1):
            reporter = AuthUserFactory()
            url = self.project.api_url + 'comment/{0}/report/'.format(comment._id)
            with assert_raises(ValueError):
                self.app.post_json(
                    url,
                    {
                        'category': 'spam',
                        'text': 'ads',
                    },
                    auth=reporter.auth,
                )
        comment.reload()
        assert_equal(comment.spam_status , Comment.UNKNOWN)

    @httpretty.activate
    def test_dont_auto_mark_if_already_ham(self):
        comment_ham = self._add_comment(
            self.project, auth=self.project.creator.auth,
        )
        comment_ham.confirm_ham(save=True)

        Comment.NUM_FLAGS_FOR_SPAM = 10
        for i in range(Comment.NUM_FLAGS_FOR_SPAM):
            reporter = AuthUserFactory()
            comment_ham.report_abuse(reporter, category='spam', text='ads',save=True)

        assert_equal(comment_ham.spam_status , Comment.HAM)

    @httpretty.activate
    def test_dont_auto_mark_if_already_ham_with_num_flags_for_spam_of_one(self):
        comment_ham = self._add_comment(
            self.project, auth=self.project.creator.auth,
        )
        comment_ham.confirm_ham(save=True)

        Comment.NUM_FLAGS_FOR_SPAM = 1
        for i in range(Comment.NUM_FLAGS_FOR_SPAM):
            reporter = AuthUserFactory()
            comment_ham.report_abuse(reporter, category='spam', text='ads',save=True)

        assert_equal(comment_ham.spam_status , Comment.HAM)

    @httpretty.activate
    def test_dont_auto_mark_if_already_spam_with_normal_num_flags_for_spam(self):
        comment_spam = self._add_comment(
            self.project, auth=self.project.creator.auth,
        )
        comment_spam.confirm_spam(save=True)
        Comment.NUM_FLAGS_FOR_SPAM = 10
        with assert_raises(ValueError):
            for i in range(Comment.NUM_FLAGS_FOR_SPAM):
                reporter = AuthUserFactory()
                comment_spam.unreport_abuse(reporter, save=True)

        assert_equal(comment_spam.spam_status, Comment.SPAM)

    @httpretty.activate
    def test_dont_auto_mark_if_already_spam_with_num_flags_for_spam_of_one(self):
        comment_spam = self._add_comment(
            self.project, auth=self.project.creator.auth,
        )
        comment_spam.confirm_spam(save=True)
        Comment.NUM_FLAGS_FOR_SPAM = 1
        with assert_raises(ValueError):
            for i in range(Comment.NUM_FLAGS_FOR_SPAM):
                reporter = AuthUserFactory()
                comment_spam.unreport_abuse(reporter, save=True)
        assert_equal(comment_spam.spam_status, Comment.SPAM)

    ###############################  TEST VIEW   #############################################
    @httpretty.activate
    def test_delete_if_marked_as_spam(self):
        comment = self._add_comment(
            self.project, auth=self.project.creator.auth,
        )
        comment.mark_as_possible_spam(save=True)

        resp =self.app.post_json(
            '/api/v1/spam_admin/mark_comment_as_spam/',
            {
                'cid':comment._id
            },
            auth=self.spam_admin.auth
        )
        comment.reload()
        assert_equal(resp.status_code, 200)
        assert_equal(comment.spam_status, Comment.SPAM)
        assert_true(comment.is_deleted)

    @httpretty.activate
    def test_marked_as_ham(self):
        comment = self._add_comment(
            self.project, auth=self.project.creator.auth,
        )
        comment.mark_as_possible_spam(save=True)

        resp = self.app.post_json(
            '/api/v1/spam_admin/mark_comment_as_ham/',
            {
                'cid':comment._id
            },
            auth=self.spam_admin.auth
        )
        comment.reload()
        assert_equal(resp.status_code, 200)
        assert_equal(comment.spam_status, Comment.HAM)
        assert_false(comment.is_deleted)

    @httpretty.activate
    def test_list_possible_spam_comments_with_spam_assassin_active(self):
        website.settings.SPAM_ASSASSIN = True
        ret=self.app.get(
            '/api/v1/spam_admin/list_comments/',
            auth=self.spam_admin.auth
        )
        previous_spam_comment_total = ret.json['total']

        for i in range(5):
            self._add_comment(
                self.project, content=self.GTUBE,auth=self.project.creator.auth,
            )
            self._add_comment(
                self.project, auth=self.project.creator.auth,
            )

        ret=self.app.get(
            '/api/v1/spam_admin/list_comments/3/',
            auth=self.spam_admin.auth
        )

        assert_equal(len(ret.json['comments']),3)
        assert_equal(previous_spam_comment_total + 5,ret.json['total'])

    @httpretty.activate
    def test_list_possible_spam_comments_with_spam_assassin_inactive(self):
        website.settings.SPAM_ASSASSIN = False
        ret=self.app.get(
            '/api/v1/spam_admin/list_comments/3/',
            auth=self.spam_admin.auth
        )
        previous_spam_list_length = len(ret.json['comments'])
        previous_spam_comment_total = ret.json['total']

        for i in range(5):
            self._add_comment(
                self.project, content=self.GTUBE,auth=self.project.creator.auth,
            )
            self._add_comment(
                self.project, auth=self.project.creator.auth,
            )

        ret=self.app.get(
            '/api/v1/spam_admin/list_comments/3/',
            auth=self.spam_admin.auth
        )

        assert_equal(len(ret.json['comments']),previous_spam_list_length)
        assert_equal(ret.json['total'],previous_spam_comment_total)

    @httpretty.activate
    def test_list_spam_comments_request_is_too_big_with_spam_assassin_active(self):
        website.settings.SPAM_ASSASSIN = True
        ret=self.app.get(
            '/api/v1/spam_admin/list_comments/',
            auth=self.spam_admin.auth
        )
        previous_total_spam_comments = ret.json['total']
        for i in range(5):
            self._add_comment(
                self.project, content=self.GTUBE,auth=self.project.creator.auth,
            )
            self._add_comment(
                self.project, auth=self.project.creator.auth,
            )

        ret=self.app.get(
            '/api/v1/spam_admin/list_comments/9999/',
            auth=self.spam_admin.auth
        )

        assert_equal(len(ret.json['comments']), previous_total_spam_comments + 5)
        assert_equal(ret.json['total'], previous_total_spam_comments + 5)

    @httpretty.activate
    def test_list_spam_comments_request_is_too_big_with_spam_assassin_inactive(self):
        website.settings.SPAM_ASSASSIN = False
        ret=self.app.get(
            '/api/v1/spam_admin/list_comments/',
            auth=self.spam_admin.auth
        )
        previous_total_spam_comments = ret.json['total']
        for i in range(5):
            self._add_comment(
                self.project, content=self.GTUBE,auth=self.project.creator.auth,
            )
            self._add_comment(
                self.project, auth=self.project.creator.auth,
            )

        ret=self.app.get(
            '/api/v1/spam_admin/list_comments/9999/',
            auth=self.spam_admin.auth
        )

        assert_equal(len(ret.json['comments']),previous_total_spam_comments)
        assert_equal(ret.json['total'],previous_total_spam_comments)

#### Projects ##############
class TestProjectSpamAdmin(OsfTestCase):
    def setUp(self):
        super(TestProjectSpamAdmin, self).setUp()
        self.project = ProjectFactory(is_public=False)
        self.project.save()
        self.GTUBE = "SPAM"
        self.spam_admin = AuthUserFactory(spam_admin=True)

    def _spamify_project(self,project):

        project.description = self.GTUBE
        project.save()

        def request_callback(request, uri, headers):
            if self.GTUBE in request.body:
                return (200, headers, json.dumps({"decision":"SPAM"}))
            return (200, headers, json.dumps({"decision":"HAM"}))

        httpretty.register_uri(
            httpretty.POST, SPAM_ASSASSIN_URL,
            body=request_callback
        )

    @httpretty.activate
    def test_project_is_spam_with_spamassassin_active(self):
        website.settings.SPAM_ASSASSIN = True
        self._spamify_project(self.project)

        assert_true(project_is_spam(self.project))

        resp = project_before_set_public(
            project=self.project,
            user=self.project.creator
            )
        assert_true(resp.get('is_spam'))

    @httpretty.activate
    def test_project_is_spam_with_spamassassin_inactive(self):
        website.settings.SPAM_ASSASSIN = False
        self._spamify_project(self.project)

        assert_false(project_is_spam(self.project))

        resp = project_before_set_public(
            project=self.project,
            user=self.project.creator
            )
        assert_false(resp.get('is_spam'))

    @httpretty.activate
    def test_project_is_ham_with_spamassassin_active(self):
        website.settings.SPAM_ASSASSIN = True
        assert_false(project_is_spam(self.project))
        resp = project_before_set_public(
            project=self.project,
            user=self.project.creator
            )
        assert_false(resp.get('is_spam'))

    @httpretty.activate
    def test_project_is_ham_with_spamassassin_inactive(self):
        website.settings.SPAM_ASSASSIN = False
        assert_false(project_is_spam(self.project))
        resp = project_before_set_public(
            project=self.project,
            user=self.project.creator
            )
        assert_false(resp.get('is_spam'))

    @httpretty.activate
    def test_project_marked_as_spam_with_spam_assassin_active(self):
        #determine number of projects that are spam beforehand
        previous=self.app.get(
            '/api/v1/spam_admin/list_projects/',
            auth=self.spam_admin.auth
        )
        previous_total = previous.json['total']

        website.settings.SPAM_ASSASSIN = True

        #spammer puts spam materials into spam project
        self._spamify_project(self.project)

        #spammer tries to make spam project public
        project_before_set_public(
            project=self.project,
            user=self.project.creator
            )
        # project is spam. It should have been marked as possible spam.
        assert_true(project_is_spam(self.project))
        assert_equal(self.project.spam_status, Node.POSSIBLE_SPAM)
        # self.project.mark_as_possible_spam(save=True) # todo: remove this.

        #spam_admin sees spam_project
        resp=self.app.get(
            '/api/v1/spam_admin/list_projects/1/',
            auth=self.spam_admin.auth
        )

        increase_in_total_possible_spam= resp.json['total'] - previous_total

        assert_equals(len(resp.json['projects']),1)
        assert_equal(increase_in_total_possible_spam , 1)

        #project is SPAM
        #spam_admin marks project as spam
        self.app.post_json(
            '/api/v1/spam_admin/mark_project_as_spam/',
            {
                'pid': self.project._id
            },
            auth=self.spam_admin.auth
        )
        self.project.reload()
        assert_equal(self.project.spam_status, Comment.SPAM)

    @httpretty.activate
    def test_project_marked_as_spam_with_spam_assassin_inactive(self):
        #determine number of projects that are spam beforehand
        previous=self.app.get(
            '/api/v1/spam_admin/list_projects/',
            auth=self.spam_admin.auth
        )
        previous_num_spam = len(previous.json['projects'])
        previous_total = previous.json['total']

        website.settings.SPAM_ASSASSIN = False

        #spammer puts spam materials into spam project
        self._spamify_project(self.project)
        assert_false(project_is_spam(self.project))

        #spammer tries to make spam project public
        project_before_set_public(
            project=self.project,
            user=self.project.creator
            )
        # project is not considered spam. It should not have been marked as possible spam.
        assert_false(project_is_spam(self.project))
        assert_equal(self.project.spam_status, Node.UNKNOWN)

        #spam_admin should not see project since it is not possible spam
        resp=self.app.get(
            '/api/v1/spam_admin/list_projects/',
            auth=self.spam_admin.auth
        )
        # difference between the previous number of spam
        # and the current number of spam should be 0
        num_spam_increase = previous_num_spam - len(resp.json['projects'])
        assert_equals(num_spam_increase, 0)
        assert_equals(resp.json['total'], previous_total)