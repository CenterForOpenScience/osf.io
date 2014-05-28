
from framework import fields
from website.addons.base import AddonNodeSettingsBase
from website.addons.twitter.settings import POSSIBLE_ACTIONS, DEFAULT_MESSAGES
from website.addons.twitter.utils import check_tweet


class AddonTwitterNodeSettings(AddonNodeSettingsBase):

    request_token_key = fields.StringField()
    request_token_secret = fields.StringField()
    oauth_key = fields.StringField()
    oauth_secret = fields.StringField()
    user_name = fields.StringField()
    displayed_tweets = fields.StringField()
    log_actions = fields.ListField(fields.StringField())
    log_messages = fields.DictionaryField(default=dict())
    tweet_queue = fields.ListField(fields.StringField())


    def to_json(self, *args, **kwargs):
        rv = super(AddonTwitterNodeSettings, self).to_json(*args, **kwargs)
        rv.update({
            'request_token_key': self.request_token_key or '',
            'request_token_secret': self.request_token_secret or '',
            'twitter_oauth_key': self.oauth_key or '',
            'twitter_oauth_secret': self.oauth_secret or '',
            'authorized_user': self.user_name or '',
            'displayed_tweets': self.displayed_tweets or '',
            'log_actions': self.log_actions or '',
            'log_messages': self.log_messages or DEFAULT_MESSAGES,
            'tweet_queue': self.tweet_queue or '',
#            'pending_tweet_num': self.pending_tweet_num or 0,
            'POSSIBLE_ACTIONS': POSSIBLE_ACTIONS,
            'DEFAULT_MESSAGES': DEFAULT_MESSAGES,
        })
        return rv
    #

    def parse_message(self, log):

        if (log.action == 'edit_title'):
            message = self.log_messages.get('edit_title_message')
            new_message = message.format(
                new_title = log.params['title_new'],
                old_title = log.params['title_original'],
            )
        elif (log.action == 'edit_description'):
            message = self.log_messages.get('edit_description_message')
            new_message = message.format(
                new_desc = log.params['description_new'],
            )
        elif (log.action == 'file_created'):
            message = self.log_messages.get('file_added_message')
            new_message = message.format(
                filename =  log.params['path'],
            )
        elif (log.action == 'tag_added'):
            message = self.log_messages.get('tag_added_message')
            new_message = message.format(
                tag_name =  log.params['tag'],
            )

        if len(new_message) > 140:
            return '$error$'
        return new_message


    def before_add_log(self, node, log):
        if log.action in self.log_actions:
            message = self.parse_message(log)
            self.tweet_queue.append(message)
            self.save()
          #check_tweet(self,message)
        return{}




