from django.apps import apps
from django.contrib.contenttypes.models import ContentType

from framework.postcommit_tasks.handlers import run_postcommit
from osf.models import NotificationSubscription
from website.project import signals

from framework.celery_tasks import app


@signals.contributor_removed.connect
def remove_contributor_from_subscriptions(node, user):
    """ Remove contributor from node subscriptions unless the user is an
        admin on any of node's parent projects.
    """
    Preprint = apps.get_model('osf.Preprint')
    DraftRegistration = apps.get_model('osf.DraftRegistration')
    # Preprints don't have subscriptions at this time
    if isinstance(node, Preprint):
        return
    if isinstance(node, DraftRegistration):
        return

    # If user still has permissions through being a contributor or group member, or has
    # admin perms on a parent, don't remove their subscription
    if not (node.is_contributor_or_group_member(user)) and user._id not in node.admin_contributor_or_group_member_ids:
        node_subscriptions = NotificationSubscription.objects.filter(
            user=user,
            user__isnull=True,
            object_id=node.id,
            content_type=ContentType.objects.get_for_model(node)
        )

        for subscription in node_subscriptions:
            subscription.delete()


@signals.node_deleted.connect
def remove_subscription(node):
    remove_subscription_task(node._id)

@signals.node_deleted.connect
def remove_supplemental_node(node):
    remove_supplemental_node_from_preprints(node._id)

@run_postcommit(once_per_request=False, celery=True)
@app.task(max_retries=5, default_retry_delay=60)
def remove_subscription_task(node_id):
    AbstractNode = apps.get_model('osf.AbstractNode')
    NotificationSubscription = apps.get_model('osf.NotificationSubscription')
    node = AbstractNode.load(node_id)
    NotificationSubscription.objects.filter(
        object_id=node.id,
        content_type=ContentType.objects.get_for_model(node),
    ).delete()


@run_postcommit(once_per_request=False, celery=True)
@app.task(max_retries=5, default_retry_delay=60)
def remove_supplemental_node_from_preprints(node_id):
    AbstractNode = apps.get_model('osf.AbstractNode')

    node = AbstractNode.load(node_id)
    for preprint in node.preprints.all():
        if preprint.node is not None:
            preprint.node = None
            preprint.save()
