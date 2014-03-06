import mock
from nose.tools import *
from webtest_plus import TestApp
import tweepy
from website.project import model

from framework.auth.decorators import Auth
import website.app
from tests.base import DbTestCase
from tests.factories import ProjectFactory, AuthUserFactory
from website.addons.twitter.model import AddonTwitterNodeSettings



#from utils import create_mock_wrapper, create_mock_key

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
        #self.project.creator.add_addon('twitter')

        #setup twitter addon
        self.node_settings = self.project.get_addon('twitter')

        self.node_settings.consumer_key = 'rohTTQSPWzgIXWw0g5dw'
        self.node_settings.consumer_secret = '7pmpjEtvoGjnSNCN2GlULrV104uVQQhg60Da7MEEy0'
        self.node_settings.log_messages= {
        'tag_added_message': 'Added tag $tag_name to our project',
        'edit_title_message': 'Changed project title from $old_title to $new_title ',
        'edit_description_message': 'Changed project description to $new_desc',
        'file_added_message':' Just added $file_name to our project',
                        }
        self.node_settings.save()



        self.node_url = '/api/v1/project/{0}/'.format(self.project._id)



    def test_oauth_start(self):

        url = self.project.api_url+'/twitter/oauth/'
        res = self.app.get(url, '', auth=self.user.auth)

        assert_equal(res.status_code, 302)


    def test_user_auth(self):

        url = self.project.api_url+'/twitter/user_auth/'
        res = self.app.get(url, '', auth=self.user.auth)

        assert_equal(self.node_settings.oauth_key, '325216328-OrWD6qHU01Ovc3HLg1cyXno0kbjRLuFpE2byvXqy')
        assert_equal(self.node_settings.oauth_secret, 'dJTzVdKSa37sV1X82YXJjV2KPgPoQjuZDH2MDRNnDLixb')
        assert_equal(self.node_settings.user_name, 'phresh_phish')

        assert_equal(res.status_code, 302)


    def test_twitter_widget(self):
        url = self.project.api_url+'/twitter/widget/'
        res = self.app.get(url, '', auth=self.user.auth)

        assert_equal(self.node_settings.user_name, 'phresh_phish')
        assert_true(self.node_settings.displayed_tweets != None)

        assert_equal(res.status_code, 200)



    def test_update_status(self):
        url = self.project.api_url+'twitter/update_status/'
        res = self.app.post_json(url, {'status':'meet my new girl holly!'}, auth=self.user.auth).maybe_follow()

        assert_equal(res.status_code, 302)



    def test_twitter_set_config(self):
        url = self.project.api_url+'twitter/settings/'
        res = self.app.post_json(url, {'edit_title':'on', 'edit_title_message':'I changed something'}, auth=self.user.auth).maybe_follow()


        #need to test that these variables are getting set properly
        #displayed_tweets should not be empty
        #log_messages should not be empty
        assert_true(self.node_settings.displayed_tweets != None)
        assert_true(self.node_settings.log_messages != None)





    def test_twitter_tweet(self):
        #building OAuthHandler object
        auth= tweepy.OAuthHandler(self.node_settings.consumer_key, self.node_settings.consumer_secret, secure=True)
        self.node_settings.oauth_key =  '325216328-OrWD6qHU01Ovc3HLg1cyXno0kbjRLuFpE2byvXqy'
        self.node_settings.oauth_secret = 'dJTzVdKSa37sV1X82YXJjV2KPgPoQjuZDH2MDRNnDLixb'
        auth.set_access_token(self.node_settings.oauth_key, self.node_settings.oauth_secret)
        api = tweepy.API(auth)

        #check to see if status gets posted, by comparing tweet count before and after tweet is sent
        previous_count = api.me().statuses_count
        self.tweet('test message')
        assert_equal(previous_count+1, api.me().statuses_count)


    def test_parser(self):
        #dummy logs
        ###### how do i create these dummy logs???? ###########




        title_log = self.node.add_log(
            action='edit_title',
            params={
                'title_new':'BATMAN BEYOND',
                'title_original': 'BATMAN ORIGINS'
            },
            auth=self.user.auth,
        )
        description_log = self.node.add_log(
            action='edit_description',
            params={
                'description_new':'a great film'
            },
            auth=self.user.auth,
        )
        file_log = self.node.add_log(
            action='file_added',
            params={
                'path':'BATMAN.PROJ'

            },
            auth=self.user.auth,
        )
        tag_log = self.node.add_log(
            action='tag_added',
            params={
                'tag':'BATMAN'
            },
            auth=self.user.auth,
        )




        #dummy messages
        title_message = self.parse_message(title_log)
        description_message = self.parse_message(description_log)
        file_message = self.parse_message(file_log)
        tag_message = self.parse_message(tag_log)

        #make sure the parser is working
        assert_equal(title_message, 'Changed project title from BATMAN ORIGINS to BATMAN BEYOND')
        assert_equal(description_message, 'Changed project description to a great film')
        assert_equal(file_message, 'Just added BATMAN.PROJ to our project')
        assert_equal(tag_message, 'Just added tag BATMAN to our project')



     # @mock.patch('website.addons.s3.model.AddonS3UserSettings.remove_iam_user')
    def test_twitter_remove_oauth(self):

        #mock_access.return_value = True

        self.node_settings.oauth_key ='325216328-OrWD6qHU01Ovc3HLg1cyXno0kbjRLuFpE2byvXqy'
        self.node_settings.oauth_secret = 'dJTzVdKSa37sV1X82YXJjV2KPgPoQjuZDH2MDRNnDLixb'
        self.node_settings.save()

        url = self.project.api_url+'twitter/oauth/delete/'
        res = self.app.post_json(
            url, auth = self.user.auth
        ).maybe_follow()

        self.node_settings.reload()
        assert_equals(self.node_settings.oauth_key, None)
        assert_equals(self.node_settings.oauth_secret, None)
        assert_equals(res.status_code, 200)

      #  url = '/api/v1/settings/twitter/'
       # self.app.delete(url, auth=self.user.auth)


