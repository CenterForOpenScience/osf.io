
from django.utils import timezone
from transitions import Machine

from api.preprint_providers.workflows import Workflows
from framework.auth import Auth
from framework.postcommit_tasks.handlers import enqueue_postcommit_task
from osf.exceptions import InvalidTransitionError
from osf.models.action import ReviewAction
from osf.models.nodelog import NodeLog
from osf.utils.workflows import DefaultStates, DEFAULT_TRANSITIONS
from website.preprints.tasks import get_and_set_preprint_identifiers
from website.reviews import signals as reviews_signals
from website.settings import DOMAIN


class BaseMachine(Machine):

    action = None
    from_state = None

    def __init__(self, machineable, state_attr, **kwargs):
        self.machineable = machineable
        self.__state_attr = state_attr
        states = kwargs.get('states', [s.value for s in DefaultStates])
        transitions = kwargs.get('transitions', DEFAULT_TRANSITIONS)
        self._validate_transitions(transitions)

        super(BaseMachine, self).__init__(
            states=states,
            transitions=transitions,
            initial=self.state,
            send_event=True,
            prepare_event=['initialize_machine'],
            ignore_invalid_triggers=True,
        )

    @property
    def state(self):
        return getattr(self.machineable, self.__state_attr)

    @state.setter
    def state(self, value):
        setattr(self.machineable, self.__state_attr, value)

    @property
    def ActionClass(self):
        raise NotImplementedError()

    def _validate_transitions(self, transitions):
        for transition in set(sum([t['after'] for t in transitions], [])):
            if not hasattr(self, transition):
                raise InvalidTransitionError(self, transition)

    def initialize_machine(self, ev):
        self.action = None
        self.from_state = ev.state

    def save_action(self, ev):
        user = ev.kwargs.get('user')
        self.action = self.ActionClass.objects.create(
            target=self.machineable,
            creator=user,
            trigger=ev.event.name,
            from_state=self.from_state.name,
            to_state=ev.state.name,
            comment=ev.kwargs.get('comment', ''),
        )

    def update_last_transitioned(self, ev):
        now = self.action.created if self.action is not None else timezone.now()
        self.machineable.date_last_transitioned = now

class ReviewsMachine(BaseMachine):
    ActionClass = ReviewAction

    def save_changes(self, ev):
        node = self.machineable.node
        node._has_abandoned_preprint = False
        now = self.action.created if self.action is not None else timezone.now()
        should_publish = self.machineable.in_public_reviews_state
        if should_publish and not self.machineable.is_published:
            if not (self.machineable.node.preprint_file and self.machineable.node.preprint_file.node == self.machineable.node):
                raise ValueError('Preprint node is not a valid preprint; cannot publish.')
            if not self.machineable.provider:
                raise ValueError('Preprint provider not specified; cannot publish.')
            if not self.machineable.subjects.exists():
                raise ValueError('Preprint must have at least one subject to be published.')
            self.machineable.date_published = now
            self.machineable.is_published = True
            enqueue_postcommit_task(get_and_set_preprint_identifiers, (), {'preprint_id': self.machineable._id}, celery=True)
        elif not should_publish and self.machineable.is_published:
            self.machineable.is_published = False
        self.machineable.save()
        node.save()

    def resubmission_allowed(self, ev):
        return self.machineable.provider.reviews_workflow == Workflows.PRE_MODERATION.value

    def notify_submit(self, ev):
        context = self.get_context()
        context['referrer'] = ev.kwargs.get('user')
        user = ev.kwargs.get('user')
        auth = Auth(user)
        self.machineable.node.add_log(
            action=NodeLog.PREPRINT_INITIATED,
            params={
                'preprint': self.machineable._id
            },
            auth=auth,
            save=False,
        )
        recipients = list(self.machineable.node.contributors)
        reviews_signals.reviews_email_submit.send(context=context, recipients=recipients)

    def notify_resubmit(self, ev):
        context = self.get_context()
        reviews_signals.reviews_email.send(creator=ev.kwargs.get('user'), context=context,
                                           template='reviews_resubmission_confirmation',
                                           action=self.action)

    def notify_accept_reject(self, ev):
        context = self.get_context()
        context['notify_comment'] = not self.machineable.provider.reviews_comments_private and self.action.comment
        context['is_rejected'] = self.action.to_state == DefaultStates.REJECTED.value
        context['was_pending'] = self.action.from_state == DefaultStates.PENDING.value
        reviews_signals.reviews_email.send(creator=ev.kwargs.get('user'), context=context,
                                           template='reviews_submission_status',
                                           action=self.action)
    def notify_edit_comment(self, ev):
        context = self.get_context()
        if not self.machineable.provider.reviews_comments_private and self.action.comment:
            reviews_signals.reviews_email.send(creator=ev.kwargs.get('user'), context=context,
                                               template='reviews_update_comment',
                                               action=self.action)

    def get_context(self):
        return {
            'domain': DOMAIN,
            'reviewable': self.machineable,
            'workflow': self.machineable.provider.reviews_workflow,
            'provider_url': self.machineable.provider.domain or '{domain}preprints/{provider_id}'.format(domain=DOMAIN, provider_id=self.machineable.provider._id),
            'provider_contact_email': self.machineable.provider.email_contact or 'contact@osf.io',
            'provider_support_email': self.machineable.provider.email_support or 'support@osf.io',
        }
