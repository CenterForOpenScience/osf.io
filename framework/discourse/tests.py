from . import *
import time

# http://stackoverflow.com/questions/3335268/are-object-literals-pythonic
class literal(object):
    def __init__(self, **kwargs):
        self.__dict__ = kwargs
    def __repr__(self):
        return 'literal(%s)' % ', '.join('%s = %r' % i for i in sorted(self.__dict__.iteritems()))
    def __str__(self):
        return repr(self)

def local_group_test():
    user1 = literal(_id='etfhq', username='acshikh@gmail.com')
    user2 = literal(_id='3ktmb', username='acshikh@cos.io')
    project_node = literal(title = 'The Test Project', _id = 'test1234',
                           contributors = [user1, user2], is_public = False)

    delete_group(project_node)
    time.sleep(0.125)

    sync_group(project_node)
    assert len(get_group_users(project_node)) == 2
    time.sleep(0.125)

    project_node.contributors = [user1]
    sync_group(project_node)
    assert len(get_group_users(project_node)) == 1
    time.sleep(0.125)

    project_node.contributors = [user1, user2]
    sync_group(project_node)
    assert len(get_group_users(project_node)) == 2
    time.sleep(0.125)

    project_node.contributors = []
    sync_group(project_node)
    assert len(get_group_users(project_node)) == 0
    time.sleep(0.125)

    delete_group(project_node)
    assert get_group_id(project_node) is None

    print('test passed')

def local_category_test():
    project_node = literal(title = 'The Test Project', _id = 'test1234', is_public = True)

    create_or_update_category(project_node)

    delete_category(project_node)
    assert get_category_id(project_node) is None

    print('test passed')

def local_comment_test():
    user1 = literal(_id='etfhq', username='acshikh@gmail.com')
    project_node = literal(title = 'The Test Project', _id = 'test1234', contributors=[user1], is_public = True)
    file_node = literal(_id='573cb78e96f6d02370c991a9', name='superRickyRobot.jpg')

    comment_id = create_comment(project_node, file_node, 'I think your robot is the coolest little bugger ever!')
    edit_comment(comment_id, 'Actually, your robot is the coolest little bugger ever!')
    delete_comment(comment_id)
    undelete_comment(comment_id)
    delete_comment(comment_id)

    print('test passed')
