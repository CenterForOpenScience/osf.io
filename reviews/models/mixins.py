# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from include import IncludeQuerySet
from transitions import Machine
from framework.auth import Auth
from framework.postcommit_tasks.handlers import enqueue_postcommit_task

from django.db import models
from django.db import transaction
from django.utils import timezone

from osf.models.action import Action
from osf.models import NodeLog
from reviews import workflow
from reviews.exceptions import InvalidTriggerError
from website.preprints.tasks import get_and_set_preprint_identifiers

from website import settings

from website.mails import mails
from website.notifications.emails import get_user_subscriptions
from website.notifications import utils
from website.notifications import emails
from website.reviews import signals as reviews_signals


class ReviewProviderMixin(models.Model):
    """A reviewed/moderated collection of objects.
    """

    REVIEWABLE_RELATION_NAME = None

    class Meta:
        abstract = True

    reviews_workflow = models.CharField(null=True, blank=True, max_length=15, choices=workflow.Workflows.choices())
    reviews_comments_private = models.NullBooleanField()
    reviews_comments_anonymous = models.NullBooleanField()

    @property
    def is_reviewed(self):
        return self.reviews_workflow is not None

    def get_reviewable_state_counts(self):
        assert self.REVIEWABLE_RELATION_NAME, 'REVIEWABLE_RELATION_NAME must be set to compute state counts'
        qs = getattr(self, self.REVIEWABLE_RELATION_NAME)
        if isinstance(qs, IncludeQuerySet):
            qs = qs.include(None)
        qs = qs.filter(node__isnull=False, node__is_deleted=False, node__is_public=True).values('reviews_state').annotate(count=models.Count('*'))
        counts = {state.value: 0 for state in workflow.States}
        counts.update({row['reviews_state']: row['count'] for row in qs if row['reviews_state'] in counts})
        return counts

    def add_admin(self, user):
        from reviews.permissions import GroupHelper
        return GroupHelper(self).get_group('admin').user_set.add(user)

    def add_moderator(self, user):
        from reviews.permissions import GroupHelper
        return GroupHelper(self).get_group('moderator').user_set.add(user)


class ReviewableMixin(models.Model):
    """Something that may be included in a reviewed collection and is subject to a reviews workflow.
    """

    class Meta:
        abstract = True

    # NOTE: reviews_state should rarely/never be modified directly -- use the state transition methods below
    reviews_state = models.CharField(max_length=15, db_index=True, choices=workflow.States.choices(), default=workflow.States.INITIAL.value)

    date_last_transitioned = models.DateTimeField(null=True, blank=True, db_index=True)

    @property
    def in_public_reviews_state(self):
        public_states = workflow.PUBLIC_STATES.get(self.provider.reviews_workflow)
        if not public_states:
            return False
        return self.reviews_state in public_states

    def reviews_submit(self, user):
        """Run the 'submit' state transition and create a corresponding Action.

        Params:
            user: The user triggering this transition.
        """
        return self.__run_transition(workflow.Triggers.SUBMIT.value, user=user)

    def reviews_accept(self, user, comment):
        """Run the 'accept' state transition and create a corresponding Action.

        Params:
            user: The user triggering this transition.
            comment: Text describing why.
        """
        return self.__run_transition(workflow.Triggers.ACCEPT.value, user=user, comment=comment)

    def reviews_reject(self, user, comment):
        """Run the 'reject' state transition and create a corresponding Action.

        Params:
            user: The user triggering this transition.
            comment: Text describing why.
        """
        return self.__run_transition(workflow.Triggers.REJECT.value, user=user, comment=comment)

    def reviews_edit_comment(self, user, comment):
        """Run the 'edit_comment' state transition and create a corresponding Action.

        Params:
            user: The user triggering this transition.
            comment: New comment text.
        """
        return self.__run_transition(workflow.Triggers.EDIT_COMMENT.value, user=user, comment=comment)

    def __run_transition(self, trigger, **kwargs):
        reviews_machine = ReviewsMachine(self, 'reviews_state')
        trigger_fn = getattr(reviews_machine, trigger)
        with transaction.atomic():
            result = trigger_fn(**kwargs)
            action = reviews_machine.action
            if not result or action is None:
                valid_triggers = reviews_machine.get_triggers(self.reviews_state)
                raise InvalidTriggerError(trigger, self.reviews_state, valid_triggers)
            return action


class ReviewsMachine(Machine):

    action = None
    from_state = None

    def __init__(self, reviewable, state_attr):
        self.reviewable = reviewable
        self.__state_attr = state_attr

        super(ReviewsMachine, self).__init__(
            states=[s.value for s in workflow.States],
            transitions=workflow.TRANSITIONS,
            initial=self.state,
            send_event=True,
            prepare_event=['initialize_machine'],
            ignore_invalid_triggers=True,
        )

    @property
    def state(self):
        return getattr(self.reviewable, self.__state_attr)

    @state.setter
    def state(self, value):
        setattr(self.reviewable, self.__state_attr, value)

    def initialize_machine(self, ev):
        self.action = None
        self.from_state = ev.state

    def save_action(self, ev):
        user = ev.kwargs.get('user')
        self.action = Action.objects.create(
            target=self.reviewable,
            creator=user,
            trigger=ev.event.name,
            from_state=self.from_state.name,
            to_state=ev.state.name,
            comment=ev.kwargs.get('comment', ''),
        )

    def update_last_transitioned(self, ev):
        now = self.action.date_created if self.action is not None else timezone.now()
        self.reviewable.date_last_transitioned = now

    def save_changes(self, ev):
        node = self.reviewable.node
        node._has_abandoned_preprint = False
        now = self.action.date_created if self.action is not None else timezone.now()
        should_publish = self.reviewable.in_public_reviews_state
        if should_publish and not self.reviewable.is_published:
            if not (self.reviewable.node.preprint_file and self.reviewable.node.preprint_file.node == self.reviewable.node):
                raise ValueError('Preprint node is not a valid preprint; cannot publish.')
            if not self.reviewable.provider:
                raise ValueError('Preprint provider not specified; cannot publish.')
            if not self.reviewable.subjects.exists():
                raise ValueError('Preprint must have at least one subject to be published.')
            self.reviewable.date_published = now
            self.reviewable.is_published = True
            enqueue_postcommit_task(get_and_set_preprint_identifiers, (), {'preprint': self.reviewable}, celery=True)
        elif not should_publish and self.reviewable.is_published:
            self.reviewable.is_published = False
        self.reviewable.save()
        node.save()

    def resubmission_allowed(self, ev):
        return self.reviewable.provider.reviews_workflow == workflow.Workflows.PRE_MODERATION.value

    def notify_submit(self, ev):
        context = self.get_context()
        context['referrer'] = ev.kwargs.get('user')
        user = ev.kwargs.get('user')
        auth = Auth(user)
        self.reviewable.node.add_log(
            action=NodeLog.PREPRINT_INITIATED,
            params={
                'preprint': self.reviewable._id
            },
            auth=auth,
            save=False,
        )
        recipients = list(self.reviewable.node.contributors)
        reviews_signals.reviews_email_submit.send(context=context, recipients=recipients)

    def notify_resubmit(self, ev):
        context = self.get_context()
        reviews_signals.reviews_email.send(creator=ev.kwargs.get('user'), context=context,
                                           template='reviews_resubmission_confirmation',
                                           action=self.action)

    def notify_accept_reject(self, ev):
        context = self.get_context()
        context['notify_comment'] = not self.reviewable.provider.reviews_comments_private and self.action.comment
        context['is_rejected'] = self.action.to_state == workflow.States.REJECTED.value
        context['was_pending'] = self.action.from_state == workflow.States.PENDING.value
        reviews_signals.reviews_email.send(creator=ev.kwargs.get('user'), context=context,
                                           template='reviews_submission_status',
                                           action=self.action)

    def notify_edit_comment(self, ev):
        context = self.get_context()
        if not self.reviewable.provider.reviews_comments_private and self.action.comment:
            reviews_signals.reviews_email.send(creator=ev.kwargs.get('user'), context=context,
                                               template='reviews_update_comment',
                                               action=self.action)

    def get_context(self):
        return {
            'domain': settings.DOMAIN,
            'reviewable': self.reviewable,
            'workflow': self.reviewable.provider.reviews_workflow,
            'provider_url': self.reviewable.provider.domain or '{domain}preprints/{provider_id}'.format(domain=settings.DOMAIN, provider_id=self.reviewable.provider._id),
            'provider_contact_email': self.reviewable.provider.email_contact or 'contact@osf.io',
            'provider_support_email': self.reviewable.provider.email_support or 'support@osf.io',
        }

# Handle email notifications including: update comment, accept, and reject of submission.
@reviews_signals.reviews_email.connect
def reviews_notification(self, creator, template, context, action):
    recipients = list(action.target.node.contributors)
    time_now = action.date_created if action is not None else timezone.now()
    node = action.target.node
    emails.notify_global_event(
        event='global_reviews',
        sender_user=creator,
        node=node,
        timestamp=time_now,
        recipients=recipients,
        template=template,
        context=context
    )

# Handle email notifications for a new submission.
@reviews_signals.reviews_email_submit.connect
def reviews_submit_notification(self, recipients, context):
    event_type = utils.find_subscription_type('global_reviews')
    for recipient in recipients:
        user_subscriptions = get_user_subscriptions(recipient, event_type)
        context['no_future_emails'] = user_subscriptions['none']
        context['is_creator'] = recipient == context['reviewable'].node.creator
        context['provider_name'] = context['reviewable'].provider.name
        mails.send_mail(
            recipient.username,
            mails.REVIEWS_SUBMISSION_CONFIRMATION,
            mimetype='html',
            user=recipient,
            **context
        )
