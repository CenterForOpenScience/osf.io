from django.core.management.base import BaseCommand
import internetarchive


class Command(BaseCommand):
    help = '"darks" an Internet Archive item, making it invisible to all users, use this to aid in ' \
           'withdraw requests or remove spam'

    def add_arguments(self, parser):
        parser.add_argument('guids', type=str, nargs='+', help='The GUIDs of the items to darken.')
        parser.add_argument('comment', type=str, help='The comment for explaining the darkening action.')
        parser.add_argument('version', type=str, help='Version of the item. Default is "v1".')
        parser.add_argument('access', type=str, help='AWS access key for our collection')
        parser.add_argument('secret', type=str, help='AWS secret key for our collection')

    def handle(self, *args, **kwargs):
        guids = kwargs['guids']
        comment = kwargs['comment']
        access_key = kwargs['access']
        secret_key = kwargs['secret']
        version = kwargs['version']

        session = internetarchive.get_session(
            config={
                "s3": {'access': access_key, 'secret': secret_key},
            },
        )

        for guid in guids:
            ia_item = session.get_item(f'osf-registrations-{guid}-{version}')
            ia_item.dark(comment)
            self.stdout.write(self.style.SUCCESS(f'Item {guid} has been darkened with comment: {comment}'))