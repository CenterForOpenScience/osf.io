from rest_framework import exceptions

from api.base.serializers import relationship_diff
from osf.models import Institution
from osf.utils import permissions as osf_permissions


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
    """Update institutions only if the user is associated with the institutions. Otherwise, raise an exception."""

    desired_institutions = Institution.objects.filter(_id__in=[item['_id'] for item in desired_institutions_data])

    # If a user wants to affiliate with a resource check that they have it.
    for inst in desired_institutions:
        if user.is_affiliated_with_institution(inst):
            resource.add_affiliated_institution(inst, user)
        else:
            raise exceptions.PermissionDenied(detail=f'User needs to be affiliated with {inst.name}')

    # If a user doesn't include an affiliation they have, then remove it.
    resource_institutions = resource.affiliated_institutions.all()
    for inst in user.get_affiliated_institutions():
        if inst in resource_institutions and inst not in desired_institutions:
            resource.remove_affiliated_institution(inst, user)
