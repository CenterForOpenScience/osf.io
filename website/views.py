# -*- coding: utf-8 -*-
import logging
import httplib as http
import datetime

import framework
from framework.auth import must_have_session_auth
from framework import Q, request
from framework.forms import utils
from framework.auth.forms import (RegistrationForm, SignInForm,
                                  ForgotPasswordForm, ResetPasswordForm)
from website.models import Guid, Node, MetaData
from framework import redirect, HTTPError, get_current_user
from website.project.forms import NewProjectForm
from website import settings

logger = logging.getLogger(__name__)


def _rescale_ratio(nodes):
    """

    :param nodes:
    :return:
    """
    if not nodes:
        return 0
    return float(max([
        len(node.logs)
        for node in nodes
    ]))


def _render_node(node):
    """

    :param node:
    :return:
    """
    return {
        'id' : node._primary_key,
        'url' : node.url,
        'api_url' : node.api_url,
    }


def _render_nodes(nodes):
    """

    :param nodes:
    :return:
    """
    return {
        'nodes' : [
            _render_node(node)
            for node in nodes
        ],
        'rescale_ratio' : _rescale_ratio(nodes),
    }


def _get_user_activity(node, user, rescale_ratio):

    # Counters
    total_count = len(node.logs)

    # Note: It's typically much faster to find logs of a given node
    # attached to a given user using node.logs.find(...) than by
    # loading the logs into Python and checking each one. However,
    # using deep caching might be even faster down the road.

    ua_count = node.logs.find(Q('user', 'eq', user)).count()
    non_ua_count = total_count - ua_count # base length of blue bar

    # Normalize over all nodes
    ua = ua_count / rescale_ratio * settings.USER_ACTIVITY_MAX_WIDTH
    non_ua = non_ua_count / rescale_ratio * settings.USER_ACTIVITY_MAX_WIDTH

    return ua_count, ua, non_ua

@must_have_session_auth
def get_dashboard_nodes(*args, **kwargs):
    user = kwargs['user']
    nodes = user.node__contributed.find(
        Q('category', 'eq', 'project') &
        Q('is_deleted', 'eq', False) &
        Q('is_registration', 'eq', False)
    )
    nodes = [
        node
        for node in nodes
        if node.category != 'project' or node.parent_id is None
    ]
    return _render_nodes(nodes)

@framework.must_be_logged_in
def dashboard(*args, **kwargs):
    user = kwargs['user']
    recent_log_ids = list(user.get_recent_log_ids())
    return {
        'logs': recent_log_ids
    }

def reproducibility():
    return framework.redirect('/project/EZcUj/wiki')

def registration_form():
    return utils.jsonify(RegistrationForm(prefix='register'))

def signin_form():
    return utils.jsonify(SignInForm())

def forgot_password_form():
    return utils.jsonify(ForgotPasswordForm(prefix='forgot_password'))

def reset_password_form():
    return utils.jsonify(ResetPasswordForm())

def new_project_form():
    return utils.jsonify(NewProjectForm())

### GUID ###

def resolve_guid(guid):

    guid_object = Guid.load(guid)
    if guid_object:
        return redirect(guid_object.referent.url)
    raise HTTPError(http.NOT_FOUND)

### Meta-data ###

def node_comment_schema():
    return {'schema': Node.comment_schema['schema']}

# todo: check whether user can view comments
def get_comments_guid(guid, collection=None):
    guid_obj = Guid.load(guid)
    annotations = guid_obj.referent.annotations
    return {'comments': [
        {
            'payload': annotation.payload,
            'user_fullname': annotation.user.fullname,
            'date': annotation.date.strftime('%Y/%m/%d %I:%M %p'),
            'comment_id': annotation._primary_key,
        }
        for annotation in annotations
        if annotation.category == 'comment'
    ]}

# todo: check whether user can post comments
def add_comment_guid(guid, collection=None):
    guid_obj = Guid.load(guid)
    user = get_current_user()
    comment = MetaData(
        target=guid_obj.referent,
        category='comment',
        schema='osf_comment',
        payload={
            'comment': request.form.get('comment'),
            'rating': request.form.get('rating'),
        },
        user=user,
        date=datetime.datetime.utcnow(),
    )
    comment.save()
