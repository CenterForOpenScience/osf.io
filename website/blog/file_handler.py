import requests
from website.addons.osfstorage.model import OsfStorageFileNode, OsfStorageNodeSettings
from modularodm import Q
from website.util import waterbutler_url_for as wb_url
from framework.auth.decorators import collect_auth


class FileHandler:

    def __init__(self, node):
        self.node = node


    def get_file_list(self):
        path = list(OsfStorageNodeSettings.find(Q("owner", "eq", self.node._id)))[0].root_node._id
        dir = list(OsfStorageFileNode.find(Q("parent", "eq", path) & Q("name", "eq", "Blog")))[0]._id
        set = list(OsfStorageFileNode.find(Q("parent", "eq", dir)))
        return set


    @collect_auth
    def read_file(self, file, auth):
        user = auth.user
        url = wb_url("download", 'osfstorage', file.path, self.node, user=user)
        response = requests.get(url)
        return response._content


    def get_posts(self, file):
        set = self.get_file_list()
        index = set.index(filter(lambda post: post.name == file, set)[0])
        curr = set[index]
        try:
            assert (index-1) >= 0
            prev = set[index-1]
        except (IndexError, AssertionError):
            prev = None
        try:
            next = set[index+1]
        except IndexError:
            next = None
        return prev, curr, next

    def get_post(self, file):
        set = self.get_file_list()
        file = file + ".md"
        return filter(lambda post: post.name == file, set)[0]
