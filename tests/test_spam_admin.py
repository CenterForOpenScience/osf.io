from __future__ import absolute_import
from nose.tools import *  # noqa PEP8 asserts


from framework.auth import Auth
from website.project.model import Comment

from website.settings import SPAM_ASSASSIN
from tests.base import (
    OsfTestCase,
)
from tests.factories import (
    ProjectFactory, AuthUserFactory
)
from framework.exceptions import HTTPError
from website.spam_admin.spam_admin_settings import SPAM_ASSASSIN_URL,SPAM_ASSASSIN_TEACHING_URL
import httpretty
from website.spam_admin.utils import train_spam, _project_is_spam
from website.project.model import Node
from website.project.views.node import project_before_set_public



class TestCommentSpamAdmin(OsfTestCase):


    def setUp(self):
        super(TestCommentSpamAdmin, self).setUp()
        self.project = ProjectFactory(is_public=True)
        self.project.save()



        #spam assassin
        self.GTUBE = "SPAM"
        self.spam_assassin_active = SPAM_ASSASSIN
        self.spam_admin = AuthUserFactory(spam_admin=True)









    def _configure_project(self, project, comment_level):

        project.comment_level = comment_level
        project.save()


    def _add_comment(self, project, content=None, **kwargs):

        def request_callback(request, uri, headers):
            if self.GTUBE in request.body:
                return (200, headers, "SPAM")
            return (200, headers, "HAM")

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
    def test_comment_added_is_spam(self):
        comment = self._add_comment(
            self.project, content = self.GTUBE, auth=self.project.creator.auth,
        )
        self.project.reload()



        assert_equal(len(self.project.commented), 1)

        if self.spam_assassin_active:
            assert_equal(comment.spam_status, Comment.POSSIBLE_SPAM)
        else:
            assert_equal(comment.spam_status, Comment.UNKNOWN)

    @httpretty.activate
    def test_comment_added_is_not_spam(self):
        comment = self._add_comment(
            self.project,auth=self.project.creator.auth,
        )
        self.project.reload()



        assert_equal(len(self.project.commented), 1)
        assert_equal(comment.spam_status , Comment.UNKNOWN)

    @httpretty.activate
    def test_train_spam_comment(self):

        httpretty.register_uri(
            httpretty.POST, SPAM_ASSASSIN_TEACHING_URL,
            body=lambda r, u, h: (200, h, "Learned")
        )

        comment = self._add_comment(
            self.project,
            content=self.GTUBE,
            auth=self.project.creator.auth,
        )
        self.project.reload()


        if self.spam_assassin_active:
            assert_true(train_spam(comment, is_spam=True))
        else:
            assert_false(train_spam(comment, is_spam=True))


    @httpretty.activate
    def test_train_ham_comment(self):

        httpretty.register_uri(
            httpretty.POST, SPAM_ASSASSIN_TEACHING_URL,
            body=lambda r,u,h: (200,h,"Learned")
        )
        comment = self._add_comment(
            self.project, auth=self.project.creator.auth,
        )
        if self.spam_assassin_active:
            assert_true(train_spam(comment, is_spam=False))
        else:
            assert_false(train_spam(comment, is_spam=False))

    @httpretty.activate
    def test_auto_mark_spam_if_flagged_enough_times(self):
        comment = self._add_comment(
            self.project, auth=self.project.creator.auth,
        )


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


        for i in range(Comment.NUM_FLAGS_FOR_SPAM):
            reporter = AuthUserFactory()
            comment_ham.report_abuse(reporter, category='spam', text='ads',save=True)

        assert_equal(comment_ham.spam_status , Comment.HAM)

    @httpretty.activate
    def test_dont_auto_mark_if_already_spam(self):
        comment_spam = self._add_comment(
            self.project, auth=self.project.creator.auth,
        )
        comment_spam.confirm_spam(save=True)

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

        if self.spam_assassin_active:
            self.app.post_json(
                '/api/v1/spam_admin/mark_comment_as_spam/',
                {
                    'cid':comment._id
                },
                auth=self.spam_admin.auth
            )
            comment.reload()
            assert_equal(comment.spam_status, Comment.SPAM)
            assert_true(comment.is_deleted)
        else:
            resp = self.app.post_json(
                '/api/v1/spam_admin/mark_comment_as_spam/',
                {
                    'cid': comment._id
                },
                auth=self.spam_admin.auth,
                expect_errors=True
            )
            comment.reload()
            assert_equal(resp.status_code, 400)
            assert_equal(comment.spam_status, Comment.POSSIBLE_SPAM)
            assert_false(comment.is_deleted)

    @httpretty.activate
    def test_marked_as_ham(self):
        comment = self._add_comment(
            self.project, auth=self.project.creator.auth,
        )
        comment.mark_as_possible_spam(save=True)
        if self.spam_assassin_active:
            self.app.post_json(
                '/api/v1/spam_admin/mark_comment_as_ham/',
                {
                    'cid':comment._id
                },
                auth=self.spam_admin.auth
            )
            comment.reload()
            assert_equal(comment.spam_status, Comment.HAM)
        else:
            resp = self.app.post_json(
                        '/api/v1/spam_admin/mark_comment_as_ham/',
                        {
                            'cid':comment._id
                        },
                        auth=self.spam_admin.auth,
                        expect_errors=True
            )
            comment.reload()
            assert_equal(resp.status_code, 400)
            assert_equal(comment.spam_status, Comment.POSSIBLE_SPAM)
            assert_false(comment.is_deleted)

    @httpretty.activate
    def test_list_possible_spam_comments(self):
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


        if self.spam_assassin_active:
            #todo: stop comments from earlier tests from saving
            assert_equal(len(ret.json['comments']),3)
            assert_true(ret.json['total']>=5)
        else:
            assert_equal(len(ret.json['comments']),0)
            assert_equal(ret.json['total'],0)

    @httpretty.activate
    def test_list_spam_comments_request_is_too_big(self):
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

        if self.spam_assassin_active:
            #todo: stop comments from earlier tests from saving
            assert_true(len(ret.json['comments'])>=5)
            assert_true(ret.json['total']>=5)
        else:
            assert_equal(len(ret.json['comments']),0)
            assert_equal(ret.json['total'],0)




#### Projects ##############
class TestProjectSpamAdmin(OsfTestCase):


    def setUp(self):
        super(TestProjectSpamAdmin, self).setUp()
        self.project = ProjectFactory(is_public=False)
        self.project.save()
        self.GTUBE = "SPAM"
        self.spam_assassin_active = SPAM_ASSASSIN
        self.spam_admin = AuthUserFactory(spam_admin=True)



    def _spamify_project(self,project):

        project.description = self.GTUBE
        project.save()

        def request_callback(request, uri, headers):
            if self.GTUBE in request.body:
                return (200, headers, "SPAM")
            return (200, headers, "HAM")

        httpretty.register_uri(
            httpretty.POST, SPAM_ASSASSIN_URL,
            body=request_callback
        )


    @httpretty.activate
    def test_project_is_spam(self):
        self._spamify_project(self.project)
        if self.spam_assassin_active:
            assert_true(_project_is_spam(self.project))
        else:
            assert_false(_project_is_spam(self.project))

        resp = project_before_set_public(
            project=self.project,
            user=self.project.creator
            )
        if self.spam_assassin_active:
            assert_true(resp.get('is_spam'))
        else:
            assert_false(resp.get('is_spam'))

    @httpretty.activate
    def test_project_is_ham(self):
        assert_false(_project_is_spam(self.project))
        resp = project_before_set_public(
            project=self.project,
            user=self.project.creator
            )
        assert_false(resp.get('is_spam'))


    @httpretty.activate
    def test_project_marked_as_spam(self):
        #spammer puts spam materials into spam project
        self._spamify_project(self.project)
        if self.spam_assassin_active:
            assert_true(_project_is_spam(self.project))
            self.project.mark_as_possible_spam(save=True)
        else:
            assert_false(_project_is_spam(self.project))

        #spammer tries to make spam project public
        project_before_set_public(
            project=self.project,
            user=self.project.creator
            )

        #spam_admin sees spam_project
        resp=self.app.get(
            '/api/v1/spam_admin/list_projects/1/',
            auth=self.spam_admin.auth
        )
        if self.spam_assassin_active:
            assert_equals(len(resp.json['projects']),1)
            assert_true(resp.json['total'] >= 1)
        else:
            assert_equals(len(resp.json['projects']), 0)
            assert_equals(resp.json['total'], 0)


        #project is SPAM
        if self.spam_assassin_active:
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
        else:
            #spam_admin marks project as spam
            res = self.app.post_json(
                '/api/v1/spam_admin/mark_project_as_spam/',
                {
                    'pid': self.project._id
                },
                auth=self.spam_admin.auth,
                expect_errors=True
            )
            assert_equal(res.status_code, 400)
            self.project.reload()
            assert_equal(self.project.spam_status, Node.UNKNOWN)


