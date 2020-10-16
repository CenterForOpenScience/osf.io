from django.utils import timezone
from transitions import Machine

from api.providers.workflows import Workflows
from framework.auth import Auth

from osf.exceptions import InvalidTransitionError
from osf.models.preprintlog import PreprintLog
from osf.models.action import ReviewAction, NodeRequestAction, PreprintRequestAction, RegistrationAction
from osf.models.sanctions import Retraction


from osf.utils import permissions
from osf.utils.workflows import (
    DefaultStates,
    DefaultTriggers,
    RegistrationStates,
    ReviewStates,
    SanctionStates,
    DEFAULT_TRANSITIONS,
    REVIEWABLE_TRANSITIONS,
    REGISTRATION_TRANSITIONS,
    SANCTION_TRANSITIONS
)
from website.mails import mails
from website.reviews import signals as reviews_signals
from website.settings import DOMAIN, OSF_SUPPORT_EMAIL, OSF_CONTACT_EMAIL


class BaseMachine(Machine):

    action = None
    from_state = None
    States = DefaultStates
    Transitions = DEFAULT_TRANSITIONS

    def __init__(self, machineable, state_attr='machine_state'):
        """
        Welcome to the machine, this is our attempt at a state machine. It was written for nodes, prerprints etc,
        but sometimes applies to sanctions, it may be to applied to anything that wants to have states and transitions.

        The general idea behind this is that we are instantiating the machine object as part of the model and it will
        validate different state changes and transitions ensuring a model will be easy to identify at a certain state.

        Here we are using the pytransitions state machine in conjunction with an "action object" which is used to store
        pre-transition info, mainly the instigator of the transition or a comment about the transition.

        :param machineable: The thing (should probably a be model) that is hold the state info.
        :param state_attr: The name of the state attribute, usually `machine_state`
        """
        self.machineable = machineable
        self.__state_attr = state_attr
        self._validate_transitions(self.Transitions)

        super(BaseMachine, self).__init__(
            states=[s.value for s in self.States],
            transitions=self.Transitions,
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
            auto=ev.kwargs.get('auto', False),
        )

    def update_last_transitioned(self, ev):
        now = self.action.created if self.action is not None else timezone.now()
        self.machineable.date_last_transitioned = now


class ReviewsMachine(BaseMachine):
    ActionClass = ReviewAction
    States = ReviewStates
    Transitions = REVIEWABLE_TRANSITIONS

    def save_changes(self, ev):
        now = self.action.created if self.action is not None else timezone.now()
        should_publish = self.machineable.in_public_reviews_state
        if self.machineable.is_retracted:
            pass  # Do not alter published state
        elif should_publish and not self.machineable.is_published:
            if not (self.machineable.primary_file and self.machineable.primary_file.target == self.machineable):
                raise ValueError('Preprint is not a valid preprint; cannot publish.')
            if not self.machineable.provider:
                raise ValueError('Preprint provider not specified; cannot publish.')
            if not self.machineable.subjects.exists():
                raise ValueError('Preprint must have at least one subject to be published.')
            self.machineable.date_published = now
            self.machineable.is_published = True
            self.machineable.ever_public = True
        elif not should_publish and self.machineable.is_published:
            self.machineable.is_published = False
        self.machineable.save()

    def resubmission_allowed(self, ev):
        return self.machineable.provider.reviews_workflow == Workflows.PRE_MODERATION.value

    def withdrawal_submitter_is_moderator_or_admin(self, submitter):
        # Returns True if the submitter of the request is a moderator or admin for the provider.
        provider = self.machineable.provider
        return provider.get_group('moderator').user_set.filter(id=submitter.id).exists() or \
               provider.get_group(permissions.ADMIN).user_set.filter(id=submitter.id).exists()

    def perform_withdraw(self, ev):
        self.machineable.date_withdrawn = self.action.created if self.action is not None else timezone.now()
        self.machineable.withdrawal_justification = ev.kwargs.get('comment', '')

    def notify_submit(self, ev):
        context = self.get_context()
        context['referrer'] = ev.kwargs.get('user')
        user = ev.kwargs.get('user')
        auth = Auth(user)
        self.machineable.add_log(
            action=PreprintLog.PUBLISHED,
            params={
                'preprint': self.machineable._id
            },
            auth=auth,
            save=False,
        )
        recipients = list(self.machineable.contributors)
        reviews_signals.reviews_email_submit.send(context=context, recipients=recipients)
        reviews_signals.reviews_email_submit_moderators_notifications.send(timestamp=timezone.now(), context=context)

    def notify_resubmit(self, ev):
        context = self.get_context()
        reviews_signals.reviews_email.send(creator=ev.kwargs.get('user'), context=context,
                                           template='reviews_resubmission_confirmation',
                                           action=self.action)

    def notify_accept_reject(self, ev):
        context = self.get_context()
        context['notify_comment'] = not self.machineable.provider.reviews_comments_private and self.action.comment
        context['comment'] = self.action.comment
        context['is_rejected'] = self.action.to_state == DefaultStates.REJECTED.value
        context['was_pending'] = self.action.from_state == DefaultStates.PENDING.value
        reviews_signals.reviews_email.send(creator=ev.kwargs.get('user'), context=context,
                                           template='reviews_submission_status',
                                           action=self.action)

    def notify_edit_comment(self, ev):
        context = self.get_context()
        context['comment'] = self.action.comment
        if not self.machineable.provider.reviews_comments_private and self.action.comment:
            reviews_signals.reviews_email.send(creator=ev.kwargs.get('user'), context=context,
                                               template='reviews_update_comment',
                                               action=self.action)

    def notify_withdraw(self, ev):
        context = self.get_context()
        context['ever_public'] = self.machineable.ever_public
        try:
            preprint_request_action = PreprintRequestAction.objects.get(target__target__id=self.machineable.id,
                                                                   from_state='pending',
                                                                   to_state='accepted',
                                                                   trigger='accept')
            context['requester'] = preprint_request_action.target.creator
        except PreprintRequestAction.DoesNotExist:
            # If there is no preprint request action, it means the withdrawal is directly initiated by admin/moderator
            context['withdrawal_submitter_is_moderator_or_admin'] = True

        for contributor in self.machineable.contributors.all():
            context['contributor'] = contributor
            if context.get('requester', None):
                context['is_requester'] = context['requester'].username == contributor.username
            mails.send_mail(
                contributor.username,
                mails.WITHDRAWAL_REQUEST_GRANTED,
                mimetype='html',
                document_type=self.machineable.provider.preprint_word,
                **context
            )

    def get_context(self):
        return {
            'domain': DOMAIN,
            'reviewable': self.machineable,
            'workflow': self.machineable.provider.reviews_workflow,
            'provider_url': self.machineable.provider.domain or '{domain}preprints/{provider_id}'.format(domain=DOMAIN, provider_id=self.machineable.provider._id),
            'provider_contact_email': self.machineable.provider.email_contact or OSF_CONTACT_EMAIL,
            'provider_support_email': self.machineable.provider.email_support or OSF_SUPPORT_EMAIL,
        }


class NodeRequestMachine(BaseMachine):
    ActionClass = NodeRequestAction

    def save_changes(self, ev):
        """ Handles contributorship changes and state transitions
        """
        if ev.event.name == DefaultTriggers.EDIT_COMMENT.value and self.action is not None:
            self.machineable.comment = self.action.comment
        self.machineable.save()

        if ev.event.name == DefaultTriggers.ACCEPT.value:
            if not self.machineable.target.is_contributor(self.machineable.creator):
                contributor_permissions = ev.kwargs.get('permissions', permissions.READ)
                self.machineable.target.add_contributor(
                    self.machineable.creator,
                    auth=Auth(ev.kwargs['user']),
                    permissions=contributor_permissions,
                    visible=ev.kwargs.get('visible', True),
                    send_email='{}_request'.format(self.machineable.request_type))

    def resubmission_allowed(self, ev):
        # TODO: [PRODUCT-395]
        return False

    def notify_submit(self, ev):
        """ Notify admins that someone is requesting access
        """
        context = self.get_context()
        context['contributors_url'] = '{}contributors/'.format(self.machineable.target.absolute_url)
        context['project_settings_url'] = '{}settings/'.format(self.machineable.target.absolute_url)

        for admin in self.machineable.target.get_users_with_perm(permissions.ADMIN):
            mails.send_mail(
                admin.username,
                mails.ACCESS_REQUEST_SUBMITTED,
                admin=admin,
                mimetype='html',
                osf_contact_email=OSF_CONTACT_EMAIL,
                **context
            )

    def notify_resubmit(self, ev):
        """ Notify admins that someone is requesting access again
        """
        # TODO: [PRODUCT-395]
        raise NotImplementedError()

    def notify_accept_reject(self, ev):
        """ Notify requester that admins have approved/denied
        """
        if ev.event.name == DefaultTriggers.REJECT.value:
            context = self.get_context()
            mails.send_mail(
                self.machineable.creator.username,
                mails.ACCESS_REQUEST_DENIED,
                mimetype='html',
                osf_contact_email=OSF_CONTACT_EMAIL,
                **context
            )
        else:
            # add_contributor sends approval notification email
            pass

    def notify_edit_comment(self, ev):
        """ Not presently required to notify for this event
        """
        pass

    def get_context(self):
        return {
            'node': self.machineable.target,
            'requester': self.machineable.creator
        }


class PreprintRequestMachine(BaseMachine):
    ActionClass = PreprintRequestAction

    def save_changes(self, ev):
        """ Handles preprint status changes and state transitions
        """
        if ev.event.name == DefaultTriggers.EDIT_COMMENT.value and self.action is not None:
            self.machineable.comment = self.action.comment
        elif ev.event.name == DefaultTriggers.SUBMIT.value:
            # If the provider is pre-moderated and target has not been through moderation, auto approve withdrawal
            if self.auto_approval_allowed():
                self.machineable.run_accept(user=self.machineable.creator, comment=self.machineable.comment, auto=True)
        elif ev.event.name == DefaultTriggers.ACCEPT.value:
            # If moderator accepts the withdrawal request
            self.machineable.target.run_withdraw(user=self.action.creator, comment=self.action.comment)
        self.machineable.save()

    def auto_approval_allowed(self):
        # Returns True if the provider is pre-moderated and the preprint is never public.
        return self.machineable.target.provider.reviews_workflow == Workflows.PRE_MODERATION.value and not self.machineable.target.ever_public

    def notify_submit(self, ev):
        context = self.get_context()
        if not self.auto_approval_allowed():
            reviews_signals.email_withdrawal_requests.send(timestamp=timezone.now(), context=context)

    def notify_accept_reject(self, ev):
        if ev.event.name == DefaultTriggers.REJECT.value:
            context = self.get_context()
            mails.send_mail(
                self.machineable.creator.username,
                mails.PREPRINT_WITHDRAWAL_REQUEST_DECLINED,
                mimetype='html',
                **context
            )
        else:
            pass

    def notify_edit_comment(self, ev):
        """ Not presently required to notify for this event
        """
        pass

    def notify_resubmit(self, ev):
        """ Notify moderators that someone is requesting withdrawal again
            Not presently required to notify for this event
        """
        # TODO
        pass

    def get_context(self):
        return {
            'reviewable': self.machineable.target,
            'requester': self.machineable.creator,
            'is_request_email': True,
        }


class RegistrationMachine(BaseMachine):
    ActionClass = RegistrationAction
    States = RegistrationStates
    Transitions = REGISTRATION_TRANSITIONS

    def save_action(self, ev):
        user = ev.kwargs.get('user')
        self.action = self.ActionClass.objects.create(
            target=self.machineable.registered_node,
            creator=user,
            trigger=ev.event.name,
            from_state=self.from_state.name,
            to_state=ev.state.name,
            comment=ev.kwargs.get('comment', ''),
        )
        self.machineable.save()

    def request_withdrawal(self, ev):
        user = ev.kwargs.get('user')
        self.machineable.refresh_from_db()
        self.machineable.registered_node.retract_registration(user)

    def request_terminate_embargo(self, ev):
        user = ev.kwargs.get('user')
        self.machineable.refresh_from_db()

        approval = self.machineable.registered_node.request_embargo_termination(user)
        approval.save()

    def withdraw_registration(self, ev):
        user = ev.kwargs.get('user')
        self.machineable.registered_node.retraction._on_complete(user)

    def reject_withdrawal(self, ev):
        user = ev.kwargs.get('user')
        self.machineable.registered_node.retraction._on_reject(user)

    def embargo_registration(self, ev):
        user = ev.kwargs.get('user')
        end_date = ev.kwargs.get('end_date')
        self.machineable.refresh_from_db()
        self.machineable.registered_node.embargo_registration(user, end_date)
        self.machineable.registered_node.refresh_from_db()

    def terminate_embargo(self, ev):
        self.machineable.registered_node.terminate_embargo()

    def edit_comment(self, ev):
        self.machineable.comment = self.action.comment
        self.machineable.save()

    def accept_draft_registration(self, ev):
        approval = self.machineable.approval
        approval.approve(self.action.creator)
        approval.save()

    def reject_draft_registration(self, ev):
        self.machineable.meta = {}
        self.machineable.save()

    def submit_draft_registration(self, ev):
        embargo_date = ev.kwargs.get('embargo_date', None)

        if embargo_date:
            submission = 'embargo'
            assert embargo_date, 'must include embargo date'
        else:
            submission = 'immediate'

        self.machineable.submit_for_review(
            self.action.creator,
            {
                'registration_choice': submission,
                'embargo_end_date': embargo_date
            },
            save=True
        )

    def withdrawal_request_fails(self, ev):
        user = ev.kwargs.get('user')
        self.machineable.registered_node.retraction._on_reject(user)
        self.machineable.registered_node.retraction.state = Retraction.REJECTED

    def force_withdrawal(self, ev):
        pass

    def notify_embargo_termination(self, ev):
        pass

    def notify_embargo(self, ev):
        pass

    def notify_withdraw(self, ev):
        pass

    def notify_accept_reject(self, ev):
        pass

    def notify_edit_comment(self, ev):
        pass

    def notify_resubmit(self, ev):
        pass

    def notify_submit(self, ev):
        pass

    def notify_withdraw_request_submitted(self, ev):
        pass

    def notify_withdraw_request_denied(self, ev):
        pass

    def notify_withdraw_request(self, ev):
        pass


class SanctionsStateMachine(Machine):

    STATE_FIELD = 'state'

    def __init__(self):
        super().__init__(
            states=SanctionStates,
            transitions=SANCTION_TRANSITIONS,
            initial_state=getattr(self, self.STATE_FIELD),
            model_attribute=self.STATE_FIELD,
            prepare_event='initialize_transition',
            send_event=True,
            ignore_invalid_triggers=True
        )

    def initialize_transition(self, event_data):
        self.action = None,
        self.from_state = event_data.state

    @property
    def target_registration(self):
        raise NotImplementedError

    def save_action(self, event_data):
        event_data.kwargs['target'] = self.machineable._get_registration()
        super().save_action(event_data)
