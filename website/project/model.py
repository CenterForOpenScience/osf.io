# -*- coding: utf-8 -*-
import logging
import re

from django.core.exceptions import ValidationError

from osf.models import OSFUser
from osf.utils import sanitize

logger = logging.getLogger(__name__)


def has_anonymous_link(node, auth):
    """check if the node is anonymous to the user

    :param Node node: Node which the user wants to visit
    :param str link: any view-only link in the current url
    :return bool anonymous: Whether the node is anonymous to the user or not
    """
    if auth.private_link:
        return auth.private_link.anonymous
    return False


def get_valid_mentioned_users_guids(comment, contributors):
    """ Get a list of valid users that are mentioned in the comment content.

    :param Node comment: Node that has content and ever_mentioned
    :param list contributors: List of contributors or group members on the node
    :return list new_mentions: List of valid contributors or group members mentioned in the comment content
    """
    mentions = set(re.findall(r'\[[@|\+].*?\]\(htt[ps]{1,2}:\/\/[a-z\d:.]+?\/([a-z\d]{5,})\/\)', comment.content))
    if not mentions:
        return []
    old_mentioned_guids = set(comment.ever_mentioned.values_list('guids___id', flat=True))
    new_mentions = mentions.difference(old_mentioned_guids)

    if OSFUser.objects.filter(is_registered=True, guids___id__in=new_mentions).count() != len(new_mentions):
        raise ValidationError('User does not exist or is not active.')
    elif contributors.filter(guids___id__in=new_mentions).count() != len(new_mentions):
        raise ValidationError('Mentioned user is not a contributor or group member.')

    return list(new_mentions)


def get_pointer_parent(pointer):
    """Given a `Pointer` object, return its parent node.
    """
    # The `parent_node` property of the `Pointer` schema refers to the parents
    # of the pointed-at `Node`, not the parents of the `Pointer`; use the
    # back-reference syntax to find the parents of the `Pointer`.
    parent_refs = pointer.node__parent
    assert len(parent_refs) == 1, 'Pointer must have exactly one parent.'
    return parent_refs[0]


def validate_title(value):
    """Validator for Node#title. Makes sure that the value exists and is not
    above 512 characters.
    """
    if value is None or not value.strip():
        raise ValidationError('Title cannot be blank.')

    value = sanitize.strip_html(value)

    if value is None or not value.strip():
        raise ValidationError('Invalid title.')

    if len(value) > 512:
        raise ValidationError('Title cannot exceed 512 characters.')

    return True


class NodeUpdateError(Exception):
    def __init__(self, reason, key, *args, **kwargs):
        super(NodeUpdateError, self).__init__(reason, *args, **kwargs)
        self.key = key
        self.reason = reason
