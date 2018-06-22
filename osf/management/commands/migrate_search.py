from django.core.management.base import BaseCommand


class Command(BaseCommand):

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)

        parser.add_argument('index-name', type=str, help='Name of the new index to create')

    def handle(self, *args, **options):
        from website.search.drivers.elasticsearch import ElasticsearchDriver

        ElasticsearchDriver(options['index-name']).migrator.teardown()
        ElasticsearchDriver(options['index-name']).migrator.migrate()
