from django.core.management.base import BaseCommand

from osf.models import CedarMetadataTemplate
from osf.external.cedar.client import CedarClient


class Command(BaseCommand):

    def handle(self, *args, **kwargs):

        # TODO: add error handling
        ids = CedarClient().retrieve_all_template_ids()
        for cedar_id in ids:
            # TODO: add error handling
            template = CedarClient().retrieve_template_by_id(cedar_id)
            schema_name = template['schema:name']
            pav_last_updated_on = template['pav:lastUpdatedOn']
            existing_versions = CedarMetadataTemplate.objects.filter(cedar_id=cedar_id)
            if not existing_versions:
                CedarMetadataTemplate.objects.create(
                    schema_name=schema_name,
                    template=template,
                    cedar_id=cedar_id,
                    template_version=1
                )
            latest_version = existing_versions.order_by('-template_version').first()
            if pav_last_updated_on != latest_version.template['pav:lastUpdatedOn']:
                CedarMetadataTemplate.objects.create(
                    schema_name=schema_name,
                    template=template,
                    cedar_id=cedar_id,
                    template_version=latest_version.template_version + 1
                )
                latest_version.active = False
                latest_version.save()
