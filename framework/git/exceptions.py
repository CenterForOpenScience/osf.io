class FileNotModified(Exception):
    def __init__(self, user_facing_message=None):
        self.message = (
            user_facing_message or
            u'File identical to current version'
        )