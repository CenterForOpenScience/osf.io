import factory
from elasticsearch_metrics.factory import MetricFactory
from osf.metrics import PreprintDownload
from osf_tests.factories import PreprintFactory


class PreprintDownloadFactory(MetricFactory):

    path = factory.Faker('lexify', text='/????????????????')
    preprint = factory.SubFactory(PreprintFactory)
    preprint_id = factory.SelfAttribute('preprint._id')
    provider_id = factory.SelfAttribute('preprint.provider._id')
    user_id = factory.Faker('lexify', text='?????')
    version = '1'

    class Meta:
        model = PreprintDownload

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        kwargs.pop('preprint', None)
        return super(PreprintDownloadFactory, cls)._build(target_class, *args, **kwargs)

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        kwargs.pop('preprint', None)
        return super(PreprintDownloadFactory, cls)._create(target_class, *args, **kwargs)
