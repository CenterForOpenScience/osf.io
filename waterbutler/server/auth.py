from stevedore import driver


class AuthHandler:

    def __init__(self, names):
        self.manager = driver.NamedExtensionManager(
            namespace='waterbutler.auth',
            names=names,
            invoke_on_load=True,
            invoke_args=(),
            name_order=True,
        )

    def fetch(self, request_handler, **kwargs):
        for extension in self.manager.extensions:
            credential = yield from extension.obj.fetch(request_handler, **kwargs)
            if credential:
                return credential
        raise AuthHandler('no valid credential found')
