# todo: move routing to new style

import framework
from framework.auth import must_have_session_auth
from framework import Q
from framework.forms import utils
from framework.auth.forms import (RegistrationForm, SignInForm,
                                  ForgotPasswordForm, ResetPasswordForm)
from website.project.forms import NewProjectForm
from website import settings

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
    return _render_nodes(nodes)

@framework.must_be_logged_in
def dashboard(*args, **kwargs):
    user = kwargs['user']
    nodes = user.node__contributed.find(
        Q('category', 'eq', 'project') &
        Q('is_deleted', 'eq', False) &
        Q('is_registration', 'eq', False)
    )
    recent_log_ids = list(user.get_recent_log_ids())

    rv = _render_nodes(nodes)
    rv['logs'] = recent_log_ids
    return rv

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
