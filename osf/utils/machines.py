
from django.utils import timezone
from transitions import Machine

from api.preprint_providers.workflows import Workflows
from framework.auth import Auth
from framework.postcommit_tasks.handlers import enqueue_postcommit_task
from osf.models.action import Action
from osf.models.nodelog import NodeLog
from osf.utils.workflows import DefaultStates, DEFAULT_TRANSITIONS
from website.preprints.tasks import get_and_set_preprint_identifiers
from website.reviews import signals as reviews_signals
from website.settings import DOMAIN

class ReviewsMachine(Machine):

    action = None
    from_state = None

    def __init__(self, reviewable, state_attr):
        self.reviewable = reviewable
        self.__state_attr = state_attr

        super(ReviewsMachine, self).__init__(
            states=[s.value for s in DefaultStates],
            transitions=DEFAULT_TRANSITIONS,
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
        return self.reviewable.provider.reviews_workflow == Workflows.PRE_MODERATION.value

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
        context['is_rejected'] = self.action.to_state == DefaultStates.REJECTED.value
        context['was_pending'] = self.action.from_state == DefaultStates.PENDING.value
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
            'domain': DOMAIN,
            'reviewable': self.reviewable,
            'workflow': self.reviewable.provider.reviews_workflow,
            'provider_url': self.reviewable.provider.domain or '{domain}preprints/{provider_id}'.format(domain=DOMAIN, provider_id=self.reviewable.provider._id),
            'provider_contact_email': self.reviewable.provider.email_contact or 'contact@osf.io',
            'provider_support_email': self.reviewable.provider.email_support or 'support@osf.io',
        }
