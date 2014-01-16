"""Check for consistency errors in file relationships.

"""

from website.app import init_app
from website import models
from framework import Q

app = init_app()

def find_missing_files():

    with_files = models.Node.find(
        Q('files_current', 'exists', True) |
        Q('files_versions', 'exists', True)
    )
    for node in with_files:
        for fname, fid in node.files_current.items():
            fobj = models.NodeFile.load(fid)
            if fobj is None:
                print 'Inconsistency: File object {} not found in MongoDB'.format(
                    fid,
                )
                continue
            try:
                version = len(node.files_versions[fname]) - 1
            except KeyError:
                print 'Inconsistency: File name {} not in files_versions of node {} ({})'.format(
                    fname,
                    node.title,
                    node._primary_key,
                )
                continue
            try:
                node.file(fobj.path, version=version)
            except:
                print 'Inconsistency: Could not load file {} ({}) on node {} ({})'.format(
                    fobj.path,
                    fobj._primary_key,
                    node.title,
                    node._primary_key,
                )

if __name__ == '__main__':
    find_missing_files()
