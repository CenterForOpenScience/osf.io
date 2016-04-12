class Commentable(object):

    @property
    def target_type(self):
        raise NotImplementedError

    @property
    def root_target_page(self):
        raise NotImplementedError

    @property
    def is_deleted(self):
        raise NotImplementedError

    def belongs_to_node(self, node_id):
        raise NotImplementedError