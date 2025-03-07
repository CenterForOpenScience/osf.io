import logging

from django.core.management.base import BaseCommand
from django.apps import apps


logger = logging.getLogger(__name__)


class Command(BaseCommand):

    def handle(self, *args, **options):
        update_unclaimed_records_for_preprint_versions()


def update_unclaimed_records_for_preprint_versions():
    Preprint = apps.get_model('osf.Preprint')
    Guid = apps.get_model('osf.Guid')
    OSFUser = apps.get_model('osf.OSFUser')
    GuidVersionsThrough = apps.get_model('osf.GuidVersionsThrough')

    for preprint in Preprint.objects.filter(
            preprintcontributor__user__is_registered=False,
    ).prefetch_related('_contributors').distinct(
        'versioned_guids__guid'
    ):
        guid, version = Guid.split_guid(preprint._id)
        latest_version_number = GuidVersionsThrough.objects.filter(guid___id=guid).last().version
        unregistered_contributors = preprint.contributor_set.filter(user__is_registered=False)
        for contributor in unregistered_contributors:
            records_key_for_current_guid = [key for key in contributor.user.unclaimed_records.keys() if guid in key]
            if records_key_for_current_guid:
                records_key_for_current_guid.sort(
                    key=lambda x: int(x.split(Preprint.GUID_VERSION_DELIMITER)[1]),
                )
                record_info = contributor.user.unclaimed_records[records_key_for_current_guid[0]]
                for current_version in range(1, int(latest_version_number) + 1):
                    preprint_id = f'{guid}{Preprint.GUID_VERSION_DELIMITER}{current_version}'
                    if preprint_id not in contributor.user.unclaimed_records.keys():
                        contributor.user.unclaimed_records[preprint_id] = contributor.user.add_unclaimed_record(
                            claim_origin=Preprint.load(preprint_id),
                            referrer=OSFUser.load(record_info['referrer_id']),
                            given_name=record_info.get('name', None),
                            email=record_info.get('email', None),
                            provided_pid=preprint_id,
                        )
            else:
                all_versions = [guid.referent for guid in GuidVersionsThrough.objects.filter(guid___id=guid)]
                for current_preprint in all_versions:
                    preprint_id = current_preprint._id
                    if preprint_id not in contributor.user.unclaimed_records.keys():
                        contributor.user.unclaimed_records[preprint_id] = contributor.user.add_unclaimed_record(
                            claim_origin=current_preprint,
                            referrer=current_preprint.creator,
                            given_name=contributor.user.fullname,
                            email=contributor.user.username,
                            provided_pid=preprint_id,
                        )
