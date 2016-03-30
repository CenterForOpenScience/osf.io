import functools
import httplib as http
import json
import operator
from copy import deepcopy

from django.contrib.auth.decorators import user_passes_test
from django.core.paginator import Paginator, EmptyPage
from django.core.urlresolvers import reverse
from django.http import HttpResponseBadRequest
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from modularodm import Q

from admin.common_auth.logs import (
    update_admin_log,
    ACCEPT_PREREG,
    REJECT_PREREG,
    COMMENT_PREREG,
)
from admin.pre_reg import serializers
from admin.pre_reg.forms import DraftRegistrationForm
from framework.exceptions import HTTPError
from framework.mongo.utils import get_or_http_error
from website.exceptions import NodeStateError
from website.files.models import FileNode
from website.project.model import MetaSchema, DraftRegistration

get_draft_or_error = functools.partial(get_or_http_error, DraftRegistration)


def get_prereg_drafts(user=None, filters=tuple()):
    prereg_schema = MetaSchema.find_one(
        Q('name', 'eq', 'Prereg Challenge') &
        Q('schema_version', 'eq', 2)
    )
    query = (
        Q('registration_schema', 'eq', prereg_schema) &
        Q('approval', 'ne', None)
    )
    if user:
        pass
        # TODO: filter by assignee; this requires multiple levels of Prereg admins-
        # one level that can see all drafts, and another than can see only the ones they're assigned.
        # As a followup to this, we need to make sure this applies to approval/rejection/commenting endpoints
        # query = query & Q('_metaschema_flags.assignee', 'eq', user._id)
    return sorted(
        DraftRegistration.find(query),
        key=operator.attrgetter('approval.initiation_date')
    )


def is_in_prereg_group(user):
    """Determines whether a user is in the prereg_group
    :param user: User wanting access to prereg material
    :return: True if prereg False if not
    """
    return user.is_in_group('prereg_group')


@user_passes_test(is_in_prereg_group)
def prereg(request):
    """Redirects to prereg page if user has prereg access
    :param request: Current logged in user
    :return: Redirect to prereg page with username, reviewers, and user obj
    """
    paginator = Paginator(get_prereg_drafts(user=request.user), 5)

    try:
        page_number = int(request.GET.get('page'))
    except (TypeError, ValueError):
        page_number = 1

    page = paginator.page(page_number)

    try:
        drafts = [serializers.serialize_draft_registration(d, json_safe=False) for d in page]
    except EmptyPage:
        drafts = []

    for draft in drafts:
        draft['form'] = DraftRegistrationForm(draft)

    context = {
        'drafts': drafts,
        'page': page,
        'IMMEDIATE': serializers.IMMEDIATE,
    }
    return render(request, 'pre_reg/prereg.html', context)


@user_passes_test(is_in_prereg_group)
def view_draft(request, draft_pk):
    """Redirects to prereg form review page if user has prereg access
    :param draft_pk: Unique id for selected draft
    :return: Redirect to prereg form review page with draft obj
    """
    draft = get_draft_or_error(draft_pk)
    context = {
        'draft': serializers.serialize_draft_registration(draft)
    }
    return render(request, 'pre_reg/edit_draft_registration.html', context)


@user_passes_test(is_in_prereg_group)
def view_file(request, node_id, provider, file_id):
    file = FileNode.load(file_id)
    wb_url = file.generate_waterbutler_url()
    return redirect(wb_url)


@csrf_exempt
@user_passes_test(is_in_prereg_group)
def approve_draft(request, draft_pk):
    """Approves current draft
    :param request: mostly for user
    :param draft_pk: Unique id for current draft
    :return: DraftRegistrationApproval obj
    """
    draft = get_draft_or_error(draft_pk)

    user = request.user.osf_user
    draft.approve(user)
    update_admin_log(
        request.user.id, draft._id, 'Draft Registration',
        'approved', action_flag=ACCEPT_PREREG
    )
    return redirect(reverse('pre_reg:prereg') + "?page={0}".format(request.POST.get('page', 1)), permanent=True)


@csrf_exempt
@user_passes_test(is_in_prereg_group)
def reject_draft(request, draft_pk):
    """Rejects current draft
    :param request: mostly for user
    :param draft_pk: Unique id for current draft
    :return: DraftRegistrationApproval obj
    """
    draft = get_draft_or_error(draft_pk)

    user = request.user.osf_user
    draft.reject(user)
    update_admin_log(
        request.user.id, draft._id, 'Draft Registration',
        'rejected', action_flag=REJECT_PREREG
    )
    return redirect(reverse('pre_reg:prereg') + "?page={0}".format(request.POST.get('page', 1)), permanent=True)


@csrf_exempt
def update_draft(request, draft_pk):
    """Updates current draft to save admin comments

    :param draft_pk: Unique id for current draft
    :return: DraftRegistration obj
    """
    data = json.loads(request.body)
    draft = get_draft_or_error(draft_pk)

    if 'admin_settings' in data:
        form = DraftRegistrationForm(data=data['admin_settings'])
        if not form.is_valid():
            return HttpResponseBadRequest("Invalid form data")
        admin_settings = form.cleaned_data
        draft.notes = admin_settings.get('notes', draft.notes)
        del admin_settings['notes']
        draft.flags = admin_settings
        draft.save()
    else:
        schema_data = data.get('schema_data', {})
        data = deepcopy(draft.registration_metadata)
        log_message = list()
        for key, value in data.items():
            comments = schema_data.get(key, {}).get('comments', [])
            for comment in comments:
                log_message.append('{}: {}'.format(key, comment['value']))
        try:
            draft.update_metadata(data)
            draft.save()
            update_admin_log(
                user_id=request.user.id,
                object_id=draft._id,
                object_repr='Draft Registration',
                message='Comments: <p>{}</p>'.format('</p><p>'.join(log_message)),
                action_flag=COMMENT_PREREG
            )
        except (NodeStateError):
            raise HTTPError(http.BAD_REQUEST)
    return JsonResponse(serializers.serialize_draft_registration(draft))
