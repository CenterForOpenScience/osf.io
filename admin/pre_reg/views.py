import functools

from django.contrib.auth.decorators import login_required  # , user_passes_test
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from django.http import JsonResponse

import json
import httplib as http

from modularodm import Q

from admin.pre_reg import serializers
from admin.pre_reg.forms import DraftRegistrationForm
# from admin.common_auth.models import MyUser

from framework.mongo.utils import get_or_http_error
from framework.exceptions import HTTPError
from website.project.model import MetaSchema, DraftRegistration
from website.exceptions import NodeStateError

get_draft_or_error = functools.partial(get_or_http_error, DraftRegistration)

def get_prereg_drafts(user=None):
    prereg_schema = MetaSchema.find_one(
        Q('name', 'eq', 'Prereg Challenge') &
        Q('schema_version', 'eq', 2)
    )
    all_drafts = DraftRegistration.find(
        Q('registration_schema', 'eq', prereg_schema) &
        Q('approval', 'ne', None)
    )
    if user:
        # TODO filter by assignee
        pass
    return all_drafts


def is_in_prereg_group(user):
    """Determines whether a user is in the prereg_group
    :param user: User wanting access to prereg material
    :return: True if prereg False if not
    """
    return user.groups.filter(name='prereg_group').exists()


@login_required
# @user_passes_test(is_in_prereg_group)
def prereg(request):
    """Redirects to prereg page if user has prereg access
    :param request: Current logged in user
    :return: Redirect to prereg page with username, reviewers, and user obj
    """
    #prereg_admin = request.user.has_perm('auth.prereg_admin')
    #user = {
    #     'username': str(request.user.username),
    #     'admin': json.dumps(prereg_admin)
    # }
    user = {
        'username': 'user_placeholder',
        'admin': 'admin_placeholder'
    }
    # reviewers = MyUser.objects.prereg_users()
    reviewers = ['admin_placeholder']

    drafts = [serializers.serialize_draft_registration(d, json_safe=False) for d in get_prereg_drafts()]
    for d in drafts:
        d['form'] = DraftRegistrationForm(d)

    context = {
        'user_info': user,
        'reviewers': reviewers,
        'drafts': drafts
    }
    return render(request, 'pre_reg/prereg.html', context)


@login_required
# @user_passes_test(is_in_prereg_group)
def prereg_form(request, draft_pk):
    """Redirects to prereg form review page if user has prereg access
    :param draft_pk: Unique id for selected draft
    :return: Redirect to prereg form review page with draft obj
    """
    draft = get_draft_or_error(draft_pk)
    context = {
        'draft': serializers.serialize_draft_registration(draft)
    }
    return render(request, 'pre_reg/edit_draft_registration.html', context)


@login_required
# @user_passes_test(is_in_prereg_group)
def get_drafts(request):
    """Determines whether a user is in the general_administrator_group
    :param user: User wanting access to administrator material
    :return: True if general administrator False if not
    """
    prereg_schema = MetaSchema.find_one(
        Q('name', 'eq', 'Prereg Challenge') &
        Q('schema_version', 'eq', 2)
    )
    all_drafts = DraftRegistration.find(
        Q('registration_schema', 'eq', prereg_schema) &
        Q('approval', 'ne', None)
    )
    serialized_drafts = {
        'drafts': [serializers.serialize_draft_registration(d) for d in all_drafts]
    }
    return JsonResponse(
        serialized_drafts
    )


@csrf_exempt
@login_required
# @user_passes_test(is_in_prereg_group)
def approve_draft(request, draft_pk):
    """Approves current draft
    :param user: Current logged in user
    :param draft_pk: Unique id for current draft
    :return: DraftRegistrationApproval obj
    """
    draft = get_draft_or_error(draft_pk)

    user = request.user.osf_user
    draft.approve(user)
    return JsonResponse({})


@csrf_exempt
@login_required
# @user_passes_test(is_in_prereg_group)
def reject_draft(request, draft_pk):
    """Rejects current draft
    :param user: Current logged in user
    :param draft_pk: Unique id for current draft
    :return: DraftRegistrationApproval obj
    """
    draft = get_draft_or_error(draft_pk)

    user = request.user.osf_user
    draft.reject(user)
    return JsonResponse({})


@csrf_exempt
@login_required
# @user_passes_test(is_in_prereg_group)
def update_draft(request, draft_pk):
    """Updates current draft to save admin comments

    :param draft_pk: Unique id for current draft
    :return: DraftRegistration obj
    """
    data = json.loads(request.body)
    draft = get_draft_or_error(draft_pk)

    schema_data = data.get('schema_data', {})
    try:
        draft.update_metadata(schema_data)
        draft.save()
    except (NodeStateError):
        raise HTTPError(http.BAD_REQUEST)
    return JsonResponse(serializers.serialize_draft_registration(draft))
