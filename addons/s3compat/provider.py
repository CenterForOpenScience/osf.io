from addons.s3compat.serializer import S3CompatSerializer

class S3CompatProvider(object):
    """An alternative to `ExternalProvider` not tied to OAuth"""

    name = 'S3 Compatible Storage'
    short_name = 's3compat'
    serializer = S3CompatSerializer

    def __init__(self, account=None):
        super(S3CompatProvider, self).__init__()

        # provide an unauthenticated session by default
        self.account = account

    def __repr__(self):
        return '<{name}: {status}>'.format(
            name=self.__class__.__name__,
            status=self.account.provider_id if self.account else 'anonymous'
        )
