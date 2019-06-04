import logging

from website.app import setup_django
setup_django()
from datetime import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta

from django.db import connection

from osf.models import AbstractNode
from addons.osfstorage.models import BaseFileNode

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# For inspecting all osfstoragefile duplicates
fetch_osfstorage_duplicates = """
    SELECT *
    FROM (
      SELECT
        target_object_id,
        name,
        parent_id,
        type,
        _path,
        count(*) AS ct
      FROM osf_basefilenode
      WHERE type = 'osf.osfstoragefile'
      GROUP BY (target_object_id, name, parent_id, type, _path)
    ) as foo
    WHERE ct > 1;
    """
# For inspecting osfstorage files where there is only one duplicate (majority case)
only_two_duplicates = """
    SELECT *
    FROM (
      SELECT
        target_object_id,
        name,
        parent_id,
        type,
        _path,
        count(*) AS ct
      FROM osf_basefilenode
      WHERE type = 'osf.osfstoragefile'
      GROUP BY (target_object_id, name, parent_id, type, _path)
    ) as foo
    WHERE ct = 2;
    """


def main():
    with connection.cursor() as cursor:
        cursor.execute(only_two_duplicates)
        duplicate_osfstorage_files = cursor.fetchall()

    print 'Inspecting {} osfstorage records, that have *one* duplicate'.format(len(duplicate_osfstorage_files))

    versions_match = 0
    sha_match = 0
    sha256_match = 0
    for record in duplicate_osfstorage_files:
        target_id = record[0] # assuming AbstractNode, is correct for this bunch.
        name = record[1]
        parent_id = record[2]
        path = record[4]
        count = record[5]
        print name, count
        node = AbstractNode.objects.get(id=target_id)
        files = node.files.filter(name=name, type='osf.osfstoragefile', parent_id=parent_id, _path=path)

        file1 = files[0]
        file2 = files[1]
        file1_versions = file1.versions.values_list('_id', flat=True)
        file2_versions = file2.versions.values_list('_id', flat=True)
        if file1_versions and file2_versions:
            v1 = file1.versions.first()
            other_v1 = file2.versions.first()
            if other_v1.metadata['sha256'] == other_v1.metadata['sha256']:
                sha256_match += 1
            if other_v1.metadata['sha1'] == other_v1.metadata['sha1']:
                sha_match += 1
        if set(file1_versions) == set(file2_versions):
            versions_match += 1

        print 'Duplicate files file versions (Point to same FileVersionObjects):'
        print file1_versions
        print file2_versions
        print 'Time between creation:'
        t_diff = relativedelta(file1.created, file2.created)
        print '{h}h {m}m {s}s'.format(h=t_diff.hours, m=t_diff.minutes, s=t_diff.seconds)
        print '-------------------------'

    print 'Total number of duplicate files with identical versions: {}'.format(versions_match)
    print 'Total number of duplicate sha1: {}'.format(sha_match)
    print 'Total number of duplicate sha256: {}'.format(sha256_match)


if __name__ == '__main__':
    main()
