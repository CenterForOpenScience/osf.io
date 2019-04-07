import logging

from website.app import setup_django
setup_django()

from osf.models import OSFUser, PreprintContributor, Preprint

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def _get_preprint_contributor(preprint, user):
    contrib = PreprintContributor.objects.filter(user=user, preprint=preprint)
    if contrib.exists():
        return contrib.get()
    return None


def main():
    # Retrieving users whose preprints were not merged
    merged_users = OSFUser.objects.filter(merged_by__isnull=False, preprints__isnull=False)
    # Use merged_list to feed back into verify_merge after script has run.
    merged_list = [{'user_id': user._id, 'preprints': [prep._id for prep in user.preprints.all()]} for user in merged_users]

    logger.info('Merged user preprints: {}'.format(merged_list))
    for user in merged_users:
        merged_by = user.merged_by
        logging.info('Merging user {}\'s preprints.. into merged_by {}'.format(user._id, merged_by._id))
        for preprint in user.preprints.all():
            user_contrib = _get_preprint_contributor(preprint, user)
            merged_by_contrib = _get_preprint_contributor(preprint, merged_by)
            print 'Preprint: {}'.format(preprint._id)
            print '    User: {}, Merged by: {}'.format(user._id, merged_by._id)
            print '   Perms: {}, {}'.format(user_contrib.permission, merged_by_contrib.permission if merged_by_contrib else None)
            print '     Bib: {}, {}'.format(user_contrib.visible, merged_by_contrib.visible if merged_by_contrib else None)
            print ' Creator: {}, {}'.format(preprint.creator == user, preprint.creator == merged_by)
            print '_______________________________________'
        merged_by._merge_users_preprints(user)


def verify_merge(merged_list):
    """
    Expecting merged list in format [{"user_id": "abcde", "preprints": ["12345"]}]
    """
    for user_dict in merged_list:
        user = OSFUser.load(user_dict['user_id'])
        merged_by = user.merged_by
        for preprint_id in user_dict['preprints']:
            preprint = Preprint.load(preprint_id)
            user_contrib = _get_preprint_contributor(preprint, user)
            merged_by_contrib = _get_preprint_contributor(preprint, merged_by)
            print 'Preprint: {}'.format(preprint._id)
            print '    User: {}, Merged by: {}'.format(user._id, merged_by._id)
            print '   Perms: {}, {}'.format(user_contrib.permission if user_contrib else None, merged_by_contrib.permission if merged_by_contrib else None)
            print '     Bib: {}, {}'.format(user_contrib.visible if user_contrib else None, merged_by_contrib.visible if merged_by_contrib else None)
            print ' Creator: {}, {}'.format(preprint.creator == user, preprint.creator == merged_by)
            print '_______________________________________'


if __name__ == '__main__':
    main()
