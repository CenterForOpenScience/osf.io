class Addon(object):

    registry = {}

    def __init__(self, fullname, shortname, provider, user_settings_model=None, node_model=None):
        self.fullname = fullname
        self.shortname = shortname
        self.provider = provider
        self.user_settings_model = user_settings_model
        self.node_model = node_model

    def __repr__(self):
        return 'AddonConfig({fullname}, {shortname}, {provider}, {user_settings_model}, {node_model})'.format(
            fullname=self.fullname,
            shortname=self.shortname,
            provider=self.provider,
            user_settings_model=self.user_settings_model,
            node_model=self.node_model,
        )

    def register(self):
        self.registry[self.shortname.lower()] = self

    @classmethod
    def get(cls, shortname):
        return cls.registry[shortname.lower()]
