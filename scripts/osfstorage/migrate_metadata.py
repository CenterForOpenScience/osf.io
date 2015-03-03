# -*- coding: utf-8 -*-
"""Script which ensures that every file version's
content_type, size, and date_modified fields are consistent
with the metadata from waterbutler.
"""
from website.addons.osfstorage.model import OsfStorageFileVersion


def main():
    for each in OsfStorageFileVersion.find():
        each.update_metadata(each.metadata)

if __name__ == '__main__':
    main()
