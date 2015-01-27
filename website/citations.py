class Citation(dict):
    pass


class CitationList(list):

    @property
    def json(self):
        """JSON-formatted string for instance and all children"""
        pass