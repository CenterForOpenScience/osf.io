"""

"""

from website.project import decorators


@decorators.must_be_valid_project
@decorators.must_be_contributor
def disable_addon(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    deleted = node.delete_addon(kwargs['addon'])
    return {'deleted': deleted}
