from babel import dates, core, Locale
from django.contrib.contenttypes.models import ContentType

from osf.models import AbstractNode, NotificationSubscription
from osf.utils.permissions import READ
from website.notifications import constants
from website.util import web_url_for

def check_node(node, event):
    """Return subscription for a particular node and event."""
    node_subscriptions = {key: [] for key in constants.NOTIFICATION_TYPES}
    if node:
        subscription = NotificationSubscription.objects.filter(
            object_id=node.id,
            content_type=ContentType.objects.get_for_model(node),
            notification_type__name=event
        )
        for notification_type in node_subscriptions:
            users = getattr(subscription, notification_type, [])
            if users:
                for user in users.exclude(date_disabled__isnull=False):
                    if node.has_permission(user, READ):
                        node_subscriptions[notification_type].append(user._id)
    return node_subscriptions


def get_user_subscriptions(user, event):
    if user.is_disabled:
        return {}
    user_subscription, _ = NotificationSubscription.objects.get_or_create(
        user=user,
        notification_type__name=event
    )
    return user_subscription


def get_node_lineage(node):
    """ Get a list of node ids in order from the node to top most project
        e.g. [parent._id, node._id]
    """
    from osf.models import Preprint
    lineage = [node._id]
    if isinstance(node, Preprint):
        return lineage

    while node.parent_id:
        node = node.parent_node
        lineage = [node._id] + lineage

    return lineage


def get_settings_url(uid, user):
    if uid == user._id:
        return web_url_for('user_notifications', _absolute=True)

    node = AbstractNode.load(uid)
    assert node, 'get_settings_url recieved an invalid Node id'
    return node.web_url_for('node_setting', _guid=True, _absolute=True)

def fix_locale(locale):
    """Atempt to fix a locale to have the correct casing, e.g. de_de -> de_DE

    This is NOT guaranteed to return a valid locale identifier.
    """
    try:
        language, territory = locale.split('_', 1)
    except ValueError:
        return locale
    else:
        return '_'.join([language, territory.upper()])

def localize_timestamp(timestamp, user):
    try:
        user_timezone = dates.get_timezone(user.timezone)
    except LookupError:
        user_timezone = dates.get_timezone('Etc/UTC')

    try:
        user_locale = Locale(user.locale)
    except core.UnknownLocaleError:
        user_locale = Locale('en')

    # Do our best to find a valid locale
    try:
        user_locale.date_formats
    except OSError:  # An IOError will be raised if locale's casing is incorrect, e.g. de_de vs. de_DE
        # Attempt to fix the locale, e.g. de_de -> de_DE
        try:
            user_locale = Locale(fix_locale(user.locale))
            user_locale.date_formats
        except (core.UnknownLocaleError, OSError):
            user_locale = Locale('en')

    formatted_date = dates.format_date(timestamp, format='full', locale=user_locale)
    formatted_time = dates.format_time(timestamp, format='short', tzinfo=user_timezone, locale=user_locale)

    return f'{formatted_time} on {formatted_date}'
