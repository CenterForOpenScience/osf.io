from . import *
from .users import *
from .topics import *

from website import settings

import requests
from furl import furl

def create_comment(node, comment_text, user=None, reply_to_post_number=None):
    if user is None or user == 'system':
        user_name = 'system'
    else:
        user_name = get_username(user)
        if user_name is None:
            raise DiscourseException('The user given does not exist in discourse!')

    url = furl(settings.DISCOURSE_SERVER_URL).join('/posts')
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = user_name

    topic_id = get_or_create_topic_id(node)
    url.args['topic_id'] = topic_id
    url.args['raw'] = comment_text
    url.args['nested_post'] = 'true'
    if reply_to_post_number:
        url.args['reply_to_post_number'] = reply_to_post_number

    result = requests.post(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to comment create request ' + result.url + ' with '
                                 + str(result.status_code) + ' ' + result.text)

    return result.json()

def edit_comment(comment_id, comment_text):
    url = furl(settings.DISCOURSE_SERVER_URL).join('/posts/' + str(comment_id))
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    url.args['post[raw]'] = comment_text

    result = requests.put(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to comment edit request ' + result.url + ' with '
                                 + str(result.status_code) + ' ' + result.text)

def delete_comment(comment_id):
    url = furl(settings.DISCOURSE_SERVER_URL).join('/posts/' + str(comment_id))
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    result = requests.delete(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to comment delete request ' + result.url + ' with '
                                 + str(result.status_code) + ' ' + result.text)

def undelete_comment(comment_id):
    url = furl(settings.DISCOURSE_SERVER_URL).join('/posts/' + str(comment_id) + '/recover')
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    result = requests.put(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to comment undelete request ' + result.url + ' with '
                                 + str(result.status_code) + ' ' + result.text)
