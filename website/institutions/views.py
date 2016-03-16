import httplib as http

from .model import Institution
from framework.exceptions import HTTPError

def view_institution(inst_id, **kwargs):
    inst = Institution.load(inst_id)
    if not inst:
        raise HTTPError(http.NOT_FOUND)
    return {
        'id': inst._id,
        'name': inst.name,
        'logo_path': inst.logo_path,
        'description': inst.description or '',
        'banner_path': inst.banner_path
    }
