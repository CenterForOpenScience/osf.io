from django.core.management.base import BaseCommand

from osf.models import CedarMetadataTemplate
from osf.external.cedar.client import CedarClient

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        ids = CedarClient().retrieve_all_template_ids()
        for cedar_id in ids:
            json = CedarClient().retrieve_template_by_id(cedar_id)
            title = json['title']
            older_versions = CedarMetadataTemplate.objects.filter(cedar_id=cedar_id).order_by('-template_version')
            latest_version = older_versions.first()
            if latest_version and json != latest_version.template:
                new_template = CedarMetadataTemplate.objects.create(
                    title=title,
                    template=json,
                    cedar_id=cedar_id,
                    template_version=latest_version.template_version + 1
                )
                new_template.save()
            else:
                new_template = CedarMetadataTemplate.objects.create(
                    title=title,
                    template=json,
                    cedar_id=cedar_id,
                    template_version=1
                )
                new_template.save()
