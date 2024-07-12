from rest_framework import exceptions
from osf.models import Institution
from osf.utils import permissions as osf_permissions
from api.base.serializers import relationship_diff


def get_institutions_to_add_remove(institutions, new_institutions):
    diff = relationship_diff(
        current_items={inst._id: inst for inst in institutions.all()},
        new_items={inst['_id']: inst for inst in new_institutions},
    )

    insts_to_add = []
    for inst_id in diff['add']:
        inst = Institution.load(inst_id)
        if not inst:
            raise exceptions.NotFound(detail=f'Institution with id "{inst_id}" was not found')
        insts_to_add.append(inst)

    return insts_to_add, diff['remove'].values()


def update_institutions(resource, new_institutions, user, post=False):
    add, remove = get_institutions_to_add_remove(
        institutions=resource.affiliated_institutions,
        new_institutions=new_institutions,
    )

    if not post:
        for inst in remove:
            if not user.is_affiliated_with_institution(inst) and not resource.has_permission(user, osf_permissions.ADMIN):
                raise exceptions.PermissionDenied(detail=f'User needs to be affiliated with {inst.name}')
            resource.remove_affiliated_institution(inst, user)

    for inst in add:
        if not user.is_affiliated_with_institution(inst):
            raise exceptions.PermissionDenied(detail=f'User needs to be affiliated with {inst.name}',)
        resource.add_affiliated_institution(inst, user)


def update_institutions_if_user_associated(resource, desired_institutions_data, user):
    desired_institutions = Institution.objects.filter(_id__in=[item['_id'] for item in desired_institutions_data])

    # If a user wants to affiliate with a resource check that they have it.
    for inst in desired_institutions:
        if user.is_affiliated_with_institution(inst):
            resource.add_affiliated_institution(inst, user)
        else:
            raise exceptions.PermissionDenied(detail=f'User needs to be affiliated with {inst.name}')

    # If a user doesn't include an affiliation they have, then remove it.
    for inst in user.get_affiliated_institutions():
        if inst in resource.affiliated_institutions.all() and inst not in desired_institutions:
            resource.remove_affiliated_institution(inst, user)
