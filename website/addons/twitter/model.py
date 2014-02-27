


import os
import urlparse
import Tkinter
import tkMessageBox

from framework import fields
import tweepy
import ctypes


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

#All log events
    POSSIBLE_ACTIONS =['project_created',
     'node_created',
    'wiki_updated',
    'contributor_added',
    'tag_added',
    'edit_title',
    'edit_description',
     'project_registered',
     'file_added',
    'file_updated',
   'node_forked']

#Default tweet messages for log events
    DEFAULT_MESSAGES = {'project_created':'Created project: ',
                        'node_created': 'Created a project node',
                        'wiki_updated': 'Updated the wiki with: ',
                        'contributor_added': ' Added a project contributor!',
                        'tag_added': 'Added tag $tag_name to our project',
                        'edit_title': 'Changed project title from $old_title to $new_title ',
                        'edit_description': 'Changed project description to $new_desc',
                        'project_registered': 'Just registered a new project!',
                        'file_added':' Just added $file_name to my project',
                        'file_updated': 'Just updated a file',
                        'node_forked': 'Just forked a node',

                        }

    #project_created : $project_title
    #node_created: $node_name
    #contributed_added: $contributor_name
    #tag_added: $tag_name
    #edit_title: $new_title, $old_title
    #edit_description: $new_description
    #project_registered: $project_name
    #file_added/updated: $file_name/$path
    #node_forked: $node_name, $contributor/$project
    #
    #


    CONSUMER_KEY = 'rohTTQSPWzgIXWw0g5dw'
    CONSUMER_SECRET = '7pmpjEtvoGjnSNCN2GlULrV104uVQQhg60Da7MEEy0'

    def to_json(self, *args, **kwargs):
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
            'CONSUMER_KEY': self.CONSUMER_KEY or '',
            'CONSUMER_SECRET': self.CONSUMER_SECRET or '',
        })
        return rv
    #
    def parse_message(self, log):
        message = self.log_messages.get(log.action+'_message')
        if (log.action == 'edit_title'):
           message = message.replace('$new_title', log.params['title_new'])
           message = message.replace('$old_title', log.params['title_original'])
        if (log.action == 'edit_description'):
           message = message.replace('new_desc', log.params['description_new'])
        if (log.action == 'file_created'):
           message = message.replace('$filename', log.params['path'])
        if (log.action == 'tag_added'):
           message = message.replace('$tag_name', log.params['tag'])

        print message

      #   self.tweet(message)
        return {}


    def before_add_log(self, node, log):
        config = node.get_addon('twitter')
        if log.action in self.log_actions:
            self.parse_message(log)
        return{}


    def register(oauth_key, oauth_secret):
        consumer_key = 'rohTTQSPWzgIXWw0g5dw'
        consumer_secret = '7pmpjEtvoGjnSNCN2GlULrV104uVQQhg60Da7MEEy0'
        auth = tweepy.OAuthHandler(consumer_key, consumer_secret, secure=True)
        auth.set_access_token(oauth_key, oauth_secret)



    def tweet(self, message):
        """Tweets message through connected account

        :param message: message to send to twitter

        :return: None
        """
#Build OAuthHandler Object
        consumer_key = 'rohTTQSPWzgIXWw0g5dw'
        consumer_secret = '7pmpjEtvoGjnSNCN2GlULrV104uVQQhg60Da7MEEy0'
        auth = tweepy.OAuthHandler(consumer_key, consumer_secret, secure=True)

#Recreate access token and call update_status() with the correct message
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