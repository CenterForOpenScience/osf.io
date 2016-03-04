from website.models import Institution

def view_institution(**kwargs):
    inst = Institution.load(kwargs.get('id'))

    return {
        'id': kwargs.get('id'),
        'name': inst.name,
        'logo_path': inst.logo_path,
        'description': inst.description if inst.description else None,
    }
