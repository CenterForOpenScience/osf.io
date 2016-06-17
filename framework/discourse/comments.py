from .common import *
from .users import *
from .topics import *

def create_comment(node, comment_text, user=None, reply_to_post_number=None):
    if user is None or user == 'system':
        user_name = 'system'
    else:
        user_name = get_username(user)
        if user_name is None:
            raise DiscourseException('The user ' + str(user) + ' given does not exist in discourse')

    data = {}
    topic_id = get_or_create_topic_id(node)
    data['topic_id'] = topic_id
    data['raw'] = comment_text
    data['nested_post'] = 'true'
    if reply_to_post_number:
        data['reply_to_post_number'] = reply_to_post_number

    return request('post', '/posts', data, user_name=user_name)

def edit_comment(comment_id, comment_text):
    data = {}
    data['post[raw]'] = comment_text
    return request('put', '/posts/' + str(comment_id), data)

def delete_comment(comment_id):
    return request('delete', '/posts/' + str(comment_id))

def undelete_comment(comment_id):
    return request('put', '/posts/' + str(comment_id) + '/recover')
