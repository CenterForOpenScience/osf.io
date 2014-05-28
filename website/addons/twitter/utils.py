import tweepy
from website.addons.twitter.settings import CONSUMER_KEY, CONSUMER_SECRET
from framework.exceptions import HTTPError



def send_tweet(twitter_node_settings, message):
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET, secure=True)
    auth.set_access_token(twitter_node_settings.oauth_key, twitter_node_settings.oauth_secret)
    api = tweepy.API(auth)
    api.update_status(message)


def check_tweet(twitter_node_settings, status):
    try:
        send_tweet(twitter_node_settings, status)
    except tweepy.TweepError as e:
        if (e[0][0].get('code') == 186):
            string = 'Your tweet is too long by '+str((len(status) - 140))+ \
                         ' characters.  Please shorten it and try again.'
            raise HTTPError(400, data={
                'message_long': string, 'message_short': 'Twitter Error'}
            )
        if (e[0][0].get('code') == 89):
            raise HTTPError(400, data = {'message_long' :
                                        'Your authentication token has expired. '
                                        'Visit the settings page to re-authenticate.',
                                        'message_short':'Twitter Error'}
            )

            #twitter_oauth_delete_node()
            #twitter.screen_name = None
            #twitter.log_messages = {}
            #twitter.log_actions ={}
            #twitter.oauth_key = None
            #twitter.oauth_secret = None
            #twitter.user_name = None
            #twitter.save()



