from website.addons.s3.serializer import S3Serializer

class S3Provider(object):
    """An alternative to `ExternalProvider` not tied to OAuth"""

    name = 'Amazon S3'
    short_name = 's3'
    serializer = S3Serializer

    def __init__(self, account=None):
        super(S3Provider, self).__init__()

        # provide an unauthenticated session by default
        self.account = account

    def __repr__(self):
        return '<{name}: {status}>'.format(
            name=self.__class__.__name__,
            status=self.account.provider_id if self.account else 'anonymous'
        )
