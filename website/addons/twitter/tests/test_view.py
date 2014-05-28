import mock
from nose.tools import *
from webtest_plus import TestApp
import unittest
import json
from framework.auth.decorators import Auth
import website.app
from tests.base import DbTestCase
from tests.factories import ProjectFactory, AuthUserFactory
from website.addons.twitter.settings import DEFAULT_MESSAGES

app = website.app.init_app(
    routes=True, set_backends=False, settings_module='website.settings'
)

class TestTwitterViewsConfig(DbTestCase):

    def setUp(self):
        self.app = TestApp(app)
        self.user = AuthUserFactory()
        self.consolidated_auth = Auth(user=self.user)
        self.auth = ('test', self.user.api_keys[0]._primary_key)

        self.project = ProjectFactory(creator=self.user)
        self.project.add_addon('twitter', auth=self.consolidated_auth)

        self.node_settings = self.project.get_addon('twitter')

        self.node_settings.log_messages= {
            'tag_added_message': 'We added tag {tag_name} to our project',
            'edit_title_message': 'We changed the project title from {old_title} to {new_title}',
            'edit_description_message': 'We changed the project description to {new_desc}',
            'file_added_message':'We just added {filename} to our project',
        }
        self.node_settings.save()

        self.node_url = '/api/v1/project/{0}/'.format(
            self.project._id
        )
    @unittest.skip('This test is not working')
    @mock.patch('website.addons.twitter.utils.send_tweet')
    def test_revoked_oauth_send_tweet(self, mock_send_tweet):

        mock_send_tweet.side_effect = tweepy.TweepError([{'message':'error', 'code':'186'}])
        url = self.project.api_url+'twitter/update_status/'
        res = self.app.post_json(
            url,
            { 'status':'....'},
            auth=self.consolidated_auth
        ).maybe_follow()
        assert_equal(res.status_code, 400)


    @mock.patch('website.addons.twitter.utils.send_tweet')
    def test_send_tweet(self, mock_send_tweet):

        mock_send_tweet.side_effect = None
        url = self.project.api_url+'twitter/update_status/'
        res = self.app.post_json(
            url,
            {'status':'....'},
            auth=self.consolidated_auth
        ).maybe_follow()
        assert_equal(res.status_code, 200)


    def test_twitter_set_config(self):
        url = self.project.api_url+'twitter/settings/'
        res = self.app.post_json(
            url,
            {'displayed_tweets':'5',
             'edit_title':'on',
             'edit_title_message':'heyo,maggots!'
            },
            auth=self.user.auth
        ).maybe_follow()
        self.node_settings.reload()
        assert_equal(self.node_settings.displayed_tweets, '5')
        assert_true(self.node_settings.log_messages.get('edit_title_message') == 'heyo,maggots!')
        assert_true('edit_title' in self.node_settings.log_actions)
        assert_equal(res.status_code, 200)




    def test_parser(self):


        title_log = self.project.add_log(
            action='edit_title',
            params={
                'title_new': 'BATMAN BEYOND',
                'title_original': 'BATMAN ORIGINS'
            },
            auth=self.consolidated_auth,
        )
        description_log = self.project.add_log(
            action='edit_description',
            params={
                'description_new':'a great film'
            },
            auth=self.consolidated_auth,
        )
        file_log = self.project.add_log(
            action='file_created',
            params={
                'path':'BATMAN.PROJ'
            },
            auth=self.consolidated_auth,
        )
        tag_log = self.project.add_log(
            action='tag_added',
            params={
                'tag':'BATMAN'
            },
            auth=self.consolidated_auth,
        )

        #dummy messages
        title_message = self.node_settings.parse_message(title_log)
        description_message = self.node_settings.parse_message(description_log)
        file_message = self.node_settings.parse_message(file_log)
        tag_message = self.node_settings.parse_message(tag_log)

        #make sure the parser is working
        assert_equal(title_message, 'We changed the project title from BATMAN ORIGINS to BATMAN BEYOND')
        assert_equal(description_message, 'We changed the project description to a great film')
        assert_equal(file_message, 'We just added BATMAN.PROJ to our project')
        assert_equal(tag_message, 'We added tag BATMAN to our project')



    def test_lengthy_tweet_before_default_edited(self):
        url = self.project.api_url+'twitter/settings/'
        res = self.app.post_json(
            url,
            {'edit_title_message':
            'This is waaaayyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy '
            'too long for a tweeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeettttt'
            },
            auth=self.user.auth
        ).maybe_follow()

        self.node_settings.reload()
        assert_equal(self.node_settings.log_messages.get('edit_title_message'),
                     DEFAULT_MESSAGES.get('edit_title_message')
        )

    def test_lengthy_tweet_after_default_edited(self):
        url = self.project.api_url+'twitter/settings/'
        res = self.app.post_json(
            url,
            {'edit_title_message':
            'This is a normal tweet length.'
            },
            auth=self.user.auth
        ).maybe_follow()
        self.node_settings.reload()
        res = self.app.post_json(
            url,
            {'edit_title_message':'This is waaaayyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy '
            'too long for a tweeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeettttt'
            },
            auth=self.user.auth
        ).maybe_follow()
        self.node_settings.reload()
        assert_equal(self.node_settings.log_messages.get('edit_title_message'),
                     'This is a normal tweet length.'
        )


    def test_length_tweet_on_add_log(self):
        title_log = self.project.add_log(
            action='edit_title',
            params={
                'title_new': 'BATMAN BEYOND',
                'title_original': 'BATMAN ORIGINS'
            },
            auth=self.consolidated_auth,
        )
        self.node_settings.log_messages['edit_title_message']='This is a really long message with an $old_title and a $new_title but it will still be waaaaaayyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy toooooooo loooooonggggggggggggggggggg'
        title_message = self.node_settings.parse_message(title_log)
        assert_equal(title_message, '$error$')


    def test_twitter_remove_oauth(self):
        self.node_settings.oauth_key ='325216328-OrWD6qHU01Ovc3HLg1cyXno0kbjRLuFpE2byvXqy'
        self.node_settings.oauth_secret = 'dJTzVdKSa37sV1X82YXJjV2KPgPoQjuZDH2MDRNnDLixb'
        self.node_settings.save()

        url = self.project.api_url+'twitter/oauth/delete/'
        res = self.app.post_json(
            url,
            auth = self.user.auth
        ).maybe_follow()

        self.node_settings.reload()
        assert_equals(self.node_settings.oauth_key, None)
        assert_equals(self.node_settings.oauth_secret, None)
        assert_equals(self.node_settings.log_messages, {})
        assert_equals(self.node_settings.log_actions, [])
        assert_equals(res.status_code, 200)


    #def test_twitter_tweet_queue(self):
    #    self.node_settings.tweet_queue = ['This is a random tweet']
    #    url = self.project.api_url+'twitter/tweet_queue/'
    #    res = self.app.get(url, auth = self.user.auth)
    #    assert_equals(res.)
    @mock.patch('website.addons.twitter.utils.send_tweet')
    def test_twitter_send_queued_tweet(self, mock_send_tweet):
        mock_send_tweet.side_effect = None
        self.node_settings.tweet_queue = ['some random status']
        self.node_settings.save()

        url = self.project.api_url+'twitter/send_queued_tweet/'
        res = self.app.post_json(
            url,
            {
                'status': 'some random status',
                'index': '0',
            },
            auth=self.user.auth
        ).maybe_follow()
        self.node_settings.reload()
        assert_equals(res.status_code, 200)
        assert_false(self.node_settings.tweet_queue)

    #def test_twitter_remove_queued_tweet(self):






