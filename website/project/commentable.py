class Commentable(object):
    """Abstract class that defines the interface for models that have comments attached to them."""

    @property
    def target_type(self):
        """ The object "type" used in the OSF v2 API. E.g. Comment objects have the type 'comments'."""
        raise NotImplementedError

    @property
    def root_target_page(self):
        """The page type associated with the object/Comment.root_target.
        E.g. For a NodeWikiPage, the page name is 'wiki'."""
        raise NotImplementedError

    @property
    def is_deleted(self):
        raise NotImplementedError

    def belongs_to_node(self, node_id):
        """Check whether an object (e.g. file, wiki, comment) is attached to the specified node."""
        raise NotImplementedError

    def get_extra_log_params(self, comment):
        """Return extra data to pass as `params` to `Node.add_log` when a new comment is
        created, edited, deleted or restored."""
        return {}
