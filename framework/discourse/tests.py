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
    user1 = literal(_id='etfhq')
    user2 = literal(_id='3ktmb')
    project_node = literal(title = 'The Test Project', _id = 'test1234',
                           contributors = [user1, user2], is_public = False)

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
