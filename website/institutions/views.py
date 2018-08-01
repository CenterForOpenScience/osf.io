import http.client as http

from framework.exceptions import HTTPError

from osf.models import Institution

def serialize_institution(inst):
    return {
        'id': inst._id,
        'name': inst.name,
        'logo_path': inst.logo_path,
        'logo_path_rounded_corners': inst.logo_path_rounded_corners,
        'description': inst.description or '',
        'banner_path': inst.banner_path,
    }


def view_institution(inst_id, **kwargs):
    try:
        inst = Institution.objects.get(_id=inst_id, is_deleted=False)
    except Institution.DoesNotExist:
        raise HTTPError(http.NOT_FOUND)
    return serialize_institution(inst)
