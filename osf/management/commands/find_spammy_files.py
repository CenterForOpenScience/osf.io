import io
import csv
from datetime import timedelta
import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from addons.osfstorage.models import OsfStorageFile
from framework.celery_tasks import app
from website import mails

logger = logging.getLogger(__name__)


@app.task(name='osf.management.commands.find_spammy_files')
def find_spammy_files(sniff_r=None, n=None, t=None, to_addrs=None):
    if not sniff_r:
        raise RuntimeError('Require arg sniff_r not found')
    if isinstance(sniff_r, str):
        sniff_r = [sniff_r]
    if isinstance(to_addrs, str):
        to_addrs = [to_addrs]
    for sniff in sniff_r:
        filename = f'spam_files_{sniff}.csv'
        filepath = f'/tmp/{filename}'
        fieldnames = ['f.name', 'f._id', 'f.created', 'n._id', 'u._id', 'u.username', 'u.fullname']
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames)
        writer.writeheader()
        qs = OsfStorageFile.objects.filter(name__iregex=sniff)
        if t:
            qs = qs.filter(created__gte=timezone.now() - timedelta(days=t))
        if n:
            qs = qs[:n]
        ct = 0
        for f in qs:
            node = f.target
            user = getattr(f.versions.first(), 'creator', node.creator)
            if f.target.deleted or user.is_disabled:
                continue
            ct += 1
            writer.writerow({
                'f.name': f.name,
                'f._id': f._id,
                'f.created': f.created,
                'n._id': node._id,
                'u._id': user._id,
                'u.username': user.username,
                'u.fullname': user.fullname
            })
        if ct:
            if to_addrs:
                for addr in to_addrs:
                    mails.send_mail(
                        mail=mails.SPAM_FILES_DETECTED,
                        to_addr=addr,
                        ct=ct,
                        sniff_r=sniff,
                        attachment_name=filename,
                        attachment_content=output.getvalue(),
                        can_change_preferences=False,
                    )
            else:
                with open(filepath, 'w') as writeFile:
                    writeFile.write(output.getvalue())

class Command(BaseCommand):
    help = '''Script to match filenames to common spammy names.'''

    def add_arguments(self, parser):
        parser.add_argument(
            '--sniff_r',
            type=str,
            nargs='+',
            required=True,
            help='Regex to match against file.name',
        )
        parser.add_argument(
            '--n',
            type=int,
            default=None,
            help='Max number of files to return',
        )
        parser.add_argument(
            '--t',
            type=int,
            default=None,
            help='Number of days to search through',
        )
        parser.add_argument(
            '--to_addrs',
            type=str,
            nargs='*',
            default=None,
            help='Email address(es) to send the resulting file to. If absent, write to csv in /tmp/',
        )

    def handle(self, *args, **options):
        script_start_time = timezone.now()
        logger.info(f'Script started time: {script_start_time}')
        logger.debug(options)

        sniff_r = options.get('sniff_r')
        n = options.get('n', None)
        t = options.get('t', None)
        to_addrs = options.get('to_addrs', None)

        find_spammy_files(sniff_r=sniff_r, n=n, t=t, to_addrs=to_addrs)

        script_finish_time = timezone.now()
        logger.info(f'Script finished time: {script_finish_time}')
        logger.info(f'Run time {script_finish_time - script_start_time}')
