from addons.s3compatb3.serializer import S3CompatB3Serializer

class S3CompatB3Provider(object):
    """An alternative to `ExternalProvider` not tied to OAuth"""

    name = 'Oracle Cloud Infrastructure Object Storage'
    short_name = 's3compatb3'
    serializer = S3CompatB3Serializer

    def __init__(self, account=None):
        super(S3CompatB3Provider, self).__init__()

        # provide an unauthenticated session by default
        self.account = account

    def __repr__(self):
        return '<{name}: {status}>'.format(
            name=self.__class__.__name__,
            status=self.account.provider_id if self.account else 'anonymous'
        )
