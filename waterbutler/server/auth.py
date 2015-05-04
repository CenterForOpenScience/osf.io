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

    def fetch(self, request_handler):
        credential = None
        for extension in self.manager.extensions:
            credential = yield from extension.obj.fetch(request_handler)
            if not credential:
                pass
        if not credential:
            raise AuthHandler('no valid credential found')
        return credential
