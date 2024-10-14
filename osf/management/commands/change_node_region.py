import logging

from django.core.management.base import BaseCommand
from google.cloud.storage.client import Client
from google.oauth2.service_account import Credentials

from osf.models import Node
from addons.osfstorage.models import Region

logger = logging.getLogger(__name__)

def change_node_region(node, dest_region, gcs_creds):
    creds = Credentials.from_service_account_info(gcs_creds)
    client = Client(credentials=creds)
    osfstorage_addon = node.get_addon('osfstorage')
    src_region = osfstorage_addon.region
    if src_region.id == dest_region.id:
        logger.warning(f'Source and destination regions match: {src_region._id}. Exiting.')
        return
    src_bucket_name = src_region.waterbutler_settings['storage']['bucket']
    dest_bucket_name = dest_region.waterbutler_settings['storage']['bucket']
    src_bucket = client.get_bucket(src_bucket_name)
    dest_bucket = client.get_bucket(dest_bucket_name)
    for f in node.files.all():
        logger.info(f'Prepraring to move file {f._id}')
        # Clone each file, so that the originals will be purged from src_region
        # Note: If this is extended to registrations, the new _ids will break SchemaResponses
        cloned_f = f.clone()
        # Retain original created date
        cloned_f.created = f.created
        # Set (G)FKs
        cloned_f.target = f.target
        cloned_f.parent = f.parent
        cloned_f.checkout = f.checkout
        cloned_f.copied_from = f.copied_from
        # Save before M2M's can be set
        cloned_f.save()
        logger.info(f'File {f._id} cloned, copying versions...')
        for v in f.versions.order_by('identifier').all():
            blob_hash = v.location['object']
            logger.info(f'Preparing to move version {blob_hash}')
            # Copy each version to dest_bucket
            src_blob = src_bucket.get_blob(blob_hash)
            src_bucket.copy_blob(src_blob, dest_bucket)
            logger.info(f'Blob {blob_hash} copied to destination, cloning version object.')
            # Clone each version, update location
            cloned_v = v.clone()
            cloned_v.location['bucket'] = dest_bucket_name
            # Retain original created date
            cloned_v.created = v.created
            # Set FKs
            cloned_v.creator = v.creator
            cloned_v.region = dest_region
            # Save before M2M's can be set
            cloned_v.save()
            cloned_f.add_version(cloned_v)
            logger.info(f'Version {blob_hash} cloned.')
        # Trash original file
        f.delete()
    logger.info('All files complete.')
    osfstorage_addon.region = dest_region
    osfstorage_addon.save()
    logger.info('Region updated. Exiting.')

class Command(BaseCommand):

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '-n',
            '--node',
            type=str,
            action='store',
            dest='node',
            help='Node._id to migrate.',
        )
        parser.add_argument(
            '-r',
            '--region',
            type=str,
            action='store',
            dest='region',
            help='Region._id to migrate files to.',
        )
        parser.add_argument(
            '-c',
            '--credentials',
            type=str,
            action='store',
            dest='gcs_creds',
            help='GCS Credentials to use. JSON string.',
        )

    def handle(self, *args, **options):
        node = Node.load(options.get('node', None))
        region = Region.load(options.get('region', None))
        gcs_creds = options.get('gcs_creds', None)
        assert node, 'Node not found'
        assert region, 'Region not found'
        assert gcs_creds, 'Credentials required'
        change_node_region(node, region, gcs_creds)
