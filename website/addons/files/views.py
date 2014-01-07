"""

"""

from website.project import decorators


@decorators.must_be_contributor_or_public
@decorators.must_have_addon('wiki')
def files_widget(*args, **kwargs):
    node = kwargs['node'] or kwargs['project']
    files = node.get_addon('files')
    rv = {
        'complete': True,
    }
    rv.update(files.config.to_json())
    return rv