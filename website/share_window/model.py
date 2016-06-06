from website.project.model import Node
from modularodm.exceptions import NoResultsFound

from modularodm import Q


class ShareWindow(object):
    '''
    "wrapper" class for Node. Used to create a Share window/
    '''

    def create(self, user):
        node = Node(creator=user)
        node.is_public = True
        self.node = node
        self.node.share_window_id = user._id

        self.node.title = user.fullname + "'s Window" #needs title for elastic search
        self.save()
        return self

    def __init__(self, node=None):
        self.node = node

    def __getattr__(self, item):
        return getattr(self.node, item)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self._id == other._id

    def __repr__(self):
        return '<Share Window ({}) with id \'{}\'>'.format(self.creator.fullname, self._id)

    def save(self):
        self.node.save()

    @classmethod
    def load(cls, key):
        from website.project.model import Node
        try:
            node = Node.find_one(Q('share_window_id', 'eq', key), allow_institution=False, allow_share_windows=True)
            return cls(node)
        except NoResultsFound:
            return None
