


import os
import urlparse

from framework import fields
import tweepy

from website import settings
from website.addons.base import AddonUserSettingsBase, AddonNodeSettingsBase
from website.addons.base import AddonError

#from . import settings as twitter_settings
#from .api import Twitter

class AddonTwitterNodeSettings(AddonNodeSettingsBase):


    oauth_key = fields.StringField()
    oauth_secret = fields.StringField()
    user_name = fields.StringField()
    displayed_tweets = fields.StringField()
    # list of user-approved log actions to tweet about
    #  log_actions = fields.ListField(fields.StringField())
    log_actions = fields.ListField(fields.StringField())
    log_messages = fields.DictionaryField(default=dict())
    user_settings = fields.ForeignField(
        'addontwitterusersettings', backref='authorized'
    )

    POSSIBLE_ACTIONS =['project_created',
     'node_created',
   'node_removed',
    'wiki_updated',
    'contributor_added',
    'contributor_removed',
    'made_public',
     'made_private',
    'tag_added',
    'tag_removed',
    'edit_title',
    'edit_description',
     'project_registered',
     'file_added',
    'file_removed',
    'file_updated',
   'node_forked']

    DEFAULT_MESSAGES = {'project_created':'i created a project!',
                        'node_created': 'Created a project node',
                        'node_removed': 'Removed a project node',
                        'edit_title': 'title edited'
                        }



    #
    #registration_data = fields.DictionaryField()

    #@property
    #def short_url(self):
    #    if self.user and self.repo:
    #        return '/'.join([self.user, self.repo])

    def to_json(self, *args, **kwargs):
        #twitter_user = user.get_addon('twitter')

        rv = super(AddonTwitterNodeSettings, self).to_json(*args, **kwargs)
        rv.update({
            'twitter_oauth_key': self.oauth_key or '',
            'twitter_oauth_secret': self.oauth_secret or '',
            'authorized_user': self.user_name or '',
            'displayed_tweets': self.displayed_tweets or '',
            'log_actions': self.log_actions or '',
            'log_messages': self.log_messages,
            'POSSIBLE_ACTIONS': self.POSSIBLE_ACTIONS or '',
            'DEFAULT_MESSAGES': self.DEFAULT_MESSAGES or '',

        })

        return rv

    def before_add_log(self, node, log):


        config = node.get_addon('twitter')
        if log.action in self.log_actions:
            self.tweet(self.log_messages.get(log.action+'_message'))
        #for i in self.log_actions :
       # if log.action in self.log_actions:
        #if log.action in self.log_messages:
                #action = self.log_actions.
           #     self.tweet(log.action)
        #if log.action in self.log_actions:
        #    api.update_status(log.action)


        return

    def tweet(self, message):
        """Tweets message through connected account

        :param message: message to send to twitter

        :return: None
        """
        consumer_key = 'rohTTQSPWzgIXWw0g5dw'
        consumer_secret = '7pmpjEtvoGjnSNCN2GlULrV104uVQQhg60Da7MEEy0'
        auth = tweepy.OAuthHandler(consumer_key, consumer_secret, secure=True)
        auth.set_access_token(self.oauth_key, self.oauth_secret)
        api = tweepy.API(auth)
        api.update_status(message)








#class AddonTwitterUserSettings(AddonUserSettingsBase):
#
#    oauth_state = fields.StringField()
#    oauth_access_token = fields.StringField()
#    oauth_token_type = fields.StringField()
#
#    @property
#    def has_auth(self):
#        return self.oauth_access_token is not None
#
#    def to_json(self, user):
#        rv = super(AddonTwitterUserSettings, self).to_json(user)
#        rv.update({
#            'authorized': self.has_auth,
#        })
#        return rv