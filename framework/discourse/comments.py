from .common import DiscourseException, request
from .users import get_username
from .topics import get_or_create_topic_id

def create_comment(node, comment_text, user=None, reply_to_post_number=None):
    """Create a comment (a post) on the topic of the project/file/wiki

    :param Node/StoredFileNode/NodeWikiPage node: the project/file/wiki whose topic should be responded to
    :param str comment_text: the comment to post on the topic
    :param User user: the user to post the comment as
    :param int reply_to_post_number: the post/comment ID in the topic to respond to
    :return int: comment/post ID of the new comment
    """
    if user is None or user == 'system':
        username = 'system'
    else:
        username = get_username(user)
        if username is None:
            raise DiscourseException('The user ' + str(user) + ' given does not exist in the osf/discourse')

    data = {}
    topic_id = get_or_create_topic_id(node)
    data['topic_id'] = topic_id
    data['raw'] = comment_text
    data['nested_post'] = 'true'
    if reply_to_post_number:
        data['reply_to_post_number'] = reply_to_post_number

    return request('post', '/posts', data, username=username)['post']['id']

def edit_comment(comment_id, comment_text):
    """Edit a comment/post

    :param int comment_id: the comment/post ID of the comment to edit
    :param str comment_text: the updated text of the comment
    """
    data = {}
    data['post[raw]'] = comment_text
    request('put', '/posts/' + str(comment_id), data)

def delete_comment(comment_id):
    """Delete a comment/post

    :param int comment_id: the comment/post ID of the comment to delete
    """
    request('delete', '/posts/' + str(comment_id))

def undelete_comment(comment_id):
    """Undelete a comment/post

    :param int comment_id: the comment/post ID of the comment to undelete
    """
    request('put', '/posts/' + str(comment_id) + '/recover')
