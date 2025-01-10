import logging
import json

from django.core.management.base import BaseCommand
from django.db import transaction
from google.cloud.storage.client import Client
from google.oauth2.service_account import Credentials

from osf.models import AbstractNode
from osf.utils.migrations import disable_auto_now_fields
from addons.osfstorage.models import Region

logger = logging.getLogger(__name__)

def _get_file_block_map(node):
    file_block_map = {}
    file_input_qids = node.registration_schema.schema_blocks.filter(
        block_type='file-input'
    ).values_list('registration_response_key', flat=True)
    for schema_response in node.schema_responses.all():
        for block in schema_response.response_blocks.filter(schema_key__in=file_input_qids):
            for file_response in block.response:
                if file_block_map.get(file_response['file_id'], False):
                    file_block_map[file_response['file_id']].append(block)
                else:
                    file_block_map[file_response['file_id']] = [block]
    return file_block_map

def _update_blocks(file_block_map, original_id, cloned_id):
    for block in file_block_map[original_id]:
        logger.info(f'Updating block {block._id} file info')
        response = []
        for file_response in block.response:
            if original_id == file_response['file_id']:
                for key in file_response['file_urls'].keys():
                    file_response['file_urls'][key] = file_response['file_urls'][key].replace(original_id, cloned_id)
            response.append(file_response)
        block.response = response
        block.save()

def _update_schema_meta(node):
    logger.info('Updating legacy schema information...')
    node.registration_responses = node.schema_responses.latest('-created').all_responses
    node.registered_meta[node.registration_schema._id] = node.expand_registration_responses()
    node.save()
    logger.info('Updated legacy schema information.')

def _copy_and_clone_versions(original_file, cloned_file, src_bucket, dest_bucket, dest_bucket_name, dest_region):
    for v in original_file.versions.order_by('identifier').all():
        blob_hash = v.location['object']
        logger.info(f'Preparing to move version {blob_hash}')
        # Copy each version to dest_bucket
        src_blob = src_bucket.get_blob(blob_hash)
        src_bucket.copy_blob(src_blob, dest_bucket)
        logger.info(f'Blob {blob_hash} copied to destination, cloning version object.')
        # Clone each version, update location
        cloned_v = v.clone()
        cloned_v.location['bucket'] = dest_bucket_name
        # Set FKs
        cloned_v.creator = v.creator
        cloned_v.region = dest_region
        # Save before M2M's can be set
        cloned_v.save()
        cloned_file.add_version(cloned_v)
        # Retain original timestamps
        cloned_v.created = v.created
        cloned_v.modified = v.modified
        cloned_v.save()
        logger.info(f'Version {blob_hash} cloned.')

def _clone_file(file_obj):
    # Clone each file, so that the originals will be purged from src_region
    cloned_f = file_obj.clone()
    # Set (G)FKs
    cloned_f.target = file_obj.target
    cloned_f.parent = file_obj.parent
    cloned_f.checkout = file_obj.checkout
    cloned_f.copied_from = file_obj.copied_from
    # Save before M2M's can be set, assigning both id and _id
    cloned_f.save()
    # Repoint Guids
    assert cloned_f.id, f'Cloned file ID not assigned for {file_obj._id}'
    file_obj.guids.update(object_id=cloned_f.id)
    # Retain original timestamps
    cloned_f.created = file_obj.created
    cloned_f.modified = file_obj.modified
    cloned_f.save()
    return cloned_f

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
    response_blocks_by_file_id = {}
    with transaction.atomic():
        with disable_auto_now_fields():
            if node.type == 'osf.registration':
                response_blocks_by_file_id = _get_file_block_map(node)
            for f in node.files.all():
                logger.info(f'Prepraring to move file {f._id}')
                cloned_f = _clone_file(f)
                if f._id in response_blocks_by_file_id:
                    logger.info(f'Prepraring to update ResponseBlocks for file {f._id}')
                    _update_blocks(response_blocks_by_file_id, f._id, cloned_f._id)
                logger.info(f'File {f._id} cloned, copying versions...')
                _copy_and_clone_versions(f, cloned_f, src_bucket, dest_bucket, dest_bucket_name, dest_region)
                # Trash original file
                f.delete()
            logger.info('All files complete.')
            if response_blocks_by_file_id:
                _update_schema_meta(node)
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
        node = AbstractNode.load(options.get('node', None))
        region = Region.load(options.get('region', None))
        gcs_creds = json.loads(options.get('gcs_creds', '{}'))
        assert node, 'Node not found'
        assert region, 'Region not found'
        assert gcs_creds, 'Credentials required'
        change_node_region(node, region, gcs_creds)
