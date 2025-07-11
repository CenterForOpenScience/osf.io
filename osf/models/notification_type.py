from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.contrib.contenttypes.models import ContentType

from osf.models.notification import Notification
from enum import Enum


class FrequencyChoices(Enum):
    NONE = 'none'
    INSTANTLY = 'instantly'
    DAILY = 'daily'
    WEEKLY = 'weekly'
    MONTHLY = 'monthly'

    @classmethod
    def choices(cls):
        return [(key.value, key.name.capitalize()) for key in cls]

def get_default_frequency_choices():
    DEFAULT_FREQUENCY_CHOICES = ['none', 'instantly', 'daily', 'weekly', 'monthly']
    return DEFAULT_FREQUENCY_CHOICES.copy()


class NotificationType(models.Model):

    class Type(str, Enum):
        # Desk notifications
        DESK_REQUEST_EXPORT = 'desk_request_export'
        DESK_REQUEST_DEACTIVATION = 'desk_request_deactivation'
        DESK_OSF_SUPPORT_EMAIL = 'desk_osf_support_email'
        DESK_REGISTRATION_BULK_UPLOAD_PRODUCT_OWNER = 'desk_registration_bulk_upload_product_owner'
        DESK_USER_REGISTRATION_BULK_UPLOAD_UNEXPECTED_FAILURE = 'desk_user_registration_bulk_upload_unexpected_failure'
        DESK_ARCHIVE_JOB_EXCEEDED = 'desk_archive_job_exceeded'
        DESK_ARCHIVE_JOB_COPY_ERROR = 'desk_archive_job_copy_error'
        DESK_ARCHIVE_JOB_FILE_NOT_FOUND = 'desk_archive_job_file_not_found'
        DESK_ARCHIVE_JOB_UNCAUGHT_ERROR = 'desk_archive_job_uncaught_error'

        # User notifications
        USER_PENDING_VERIFICATION = 'user_pending_verification'
        USER_PENDING_VERIFICATION_REGISTERED = 'user_pending_verification_registered'
        USER_STORAGE_CAP_EXCEEDED_ANNOUNCEMENT = 'user_storage_cap_exceeded_announcement'
        USER_SPAM_BANNED = 'user_spam_banned'
        USER_REQUEST_DEACTIVATION_COMPLETE = 'user_request_deactivation_complete'
        USER_PRIMARY_EMAIL_CHANGED = 'user_primary_email_changed'
        USER_INSTITUTION_DEACTIVATION = 'user_institution_deactivation'
        USER_FORGOT_PASSWORD = 'user_forgot_password'
        USER_FORGOT_PASSWORD_INSTITUTION = 'user_forgot_password_institution'
        USER_REQUEST_EXPORT = 'user_request_export'
        USER_CONTRIBUTOR_ADDED_OSF_PREPRINT = 'user_contributor_added_osf_preprint'
        USER_CONTRIBUTOR_ADDED_DEFAULT = 'user_contributor_added_default'
        USER_DUPLICATE_ACCOUNTS_OSF4I = 'user_duplicate_accounts_osf4i'
        USER_EXTERNAL_LOGIN_LINK_SUCCESS = 'user_external_login_link_success'
        USER_REGISTRATION_BULK_UPLOAD_FAILURE_ALL = 'user_registration_bulk_upload_failure_all'
        USER_REGISTRATION_BULK_UPLOAD_SUCCESS_PARTIAL = 'user_registration_bulk_upload_success_partial'
        USER_REGISTRATION_BULK_UPLOAD_SUCCESS_ALL = 'user_registration_bulk_upload_success_all'
        USER_ADD_SSO_EMAIL_OSF4I = 'user_add_sso_email_osf4i'
        USER_WELCOME_OSF4I = 'user_welcome_osf4i'
        USER_ARCHIVE_JOB_EXCEEDED = 'user_archive_job_exceeded'
        USER_ARCHIVE_JOB_COPY_ERROR = 'user_archive_job_copy_error'
        USER_ARCHIVE_JOB_FILE_NOT_FOUND = 'user_archive_job_file_not_found'
        USER_ARCHIVE_JOB_UNCAUGHT_ERROR = 'user_archive_job_uncaught_error'
        USER_COMMENT_REPLIES = 'user_comment_replies'
        USER_COMMENTS = 'user_comments'
        USER_FILE_UPDATED = 'user_file_updated'
        USER_COMMENT_MENTIONS = 'user_mentions'
        USER_REVIEWS = 'user_reviews'
        USER_PASSWORD_RESET = 'user_password_reset'
        USER_CONTRIBUTOR_ADDED_DRAFT_REGISTRATION = 'user_contributor_added_draft_registration'
        USER_EXTERNAL_LOGIN_CONFIRM_EMAIL_CREATE = 'user_external_login_confirm_email_create'
        USER_EXTERNAL_LOGIN_CONFIRM_EMAIL_LINK = 'user_external_login_confirm_email_link'
        USER_CONFIRM_MERGE = 'user_confirm_merge'
        USER_CONFIRM_EMAIL = 'user_confirm_email'
        USER_INITIAL_CONFIRM_EMAIL = 'user_initial_confirm_email'
        USER_INVITE_DEFAULT = 'user_invite_default'
        USER_PENDING_INVITE = 'user_pending_invite'
        USER_FORWARD_INVITE = 'user_forward_invite'
        USER_FORWARD_INVITE_REGISTERED = 'user_forward_invite_registered'
        USER_INVITE_DRAFT_REGISTRATION = 'user_invite_draft_registration'
        USER_INVITE_OSF_PREPRINT = 'user_invite_osf_preprint'

        # Node notifications
        NODE_COMMENT = 'node_comments'
        NODE_FILES_UPDATED = 'node_files_updated'
        NODE_AFFILIATION_CHANGED = 'node_affiliation_changed'
        NODE_REQUEST_ACCESS_SUBMITTED = 'node_access_request_submitted'
        NODE_REQUEST_ACCESS_DENIED = 'node_request_access_denied'
        NODE_FORK_COMPLETED = 'node_fork_completed'
        NODE_FORK_FAILED = 'node_fork_failed'
        NODE_REQUEST_INSTITUTIONAL_ACCESS_REQUEST = 'node_request_institutional_access_request'
        NODE_CONTRIBUTOR_ADDED_ACCESS_REQUEST = 'node_contributor_added_access_request'
        NODE_PENDING_EMBARGO_ADMIN = 'node_pending_embargo_admin'
        NODE_PENDING_EMBARGO_NON_ADMIN = 'node_pending_embargo_non_admin'
        NODE_PENDING_RETRACTION_NON_ADMIN = 'node_pending_retraction_non_admin'
        NODE_PENDING_RETRACTION_ADMIN = 'node_pending_retraction_admin'
        NODE_PENDING_REGISTRATION_NON_ADMIN = 'node_pending_registration_non_admin'
        NODE_PENDING_REGISTRATION_ADMIN = 'node_pending_registration_admin'
        NODE_PENDING_EMBARGO_TERMINATION_NON_ADMIN = 'node_pending_embargo_termination_non_admin'
        NODE_PENDING_EMBARGO_TERMINATION_ADMIN = 'node_pending_embargo_termination_admin'

        # Provider notifications
        PROVIDER_NEW_PENDING_SUBMISSIONS = 'provider_new_pending_submissions'
        PROVIDER_REVIEWS_SUBMISSION_CONFIRMATION = 'provider_reviews_submission_confirmation'
        PROVIDER_REVIEWS_MODERATOR_SUBMISSION_CONFIRMATION = 'provider_reviews_moderator_submission_confirmation'
        PROVIDER_REVIEWS_WITHDRAWAL_REQUESTED = 'preprint_request_withdrawal_requested'
        PROVIDER_REVIEWS_REJECT_CONFIRMATION = 'provider_reviews_reject_confirmation'
        PROVIDER_REVIEWS_ACCEPT_CONFIRMATION = 'provider_reviews_accept_confirmation'
        PROVIDER_REVIEWS_RESUBMISSION_CONFIRMATION = 'provider_reviews_resubmission_confirmation'
        PROVIDER_REVIEWS_COMMENT_EDITED = 'provider_reviews_comment_edited'
        PROVIDER_CONTRIBUTOR_ADDED_PREPRINT = 'provider_contributor_added_preprint'
        PROVIDER_CONFIRM_EMAIL_MODERATION = 'provider_confirm_email_moderation'
        PROVIDER_MODERATOR_ADDED = 'provider_moderator_added'
        PROVIDER_CONFIRM_EMAIL_PREPRINTS = 'provider_confirm_email_preprints'
        PROVIDER_USER_INVITE_PREPRINT = 'provider_user_invite_preprint'

        # Preprint notifications
        PREPRINT_REQUEST_WITHDRAWAL_APPROVED = 'preprint_request_withdrawal_approved'
        PREPRINT_REQUEST_WITHDRAWAL_DECLINED = 'preprint_request_withdrawal_declined'
        PREPRINT_CONTRIBUTOR_ADDED_PREPRINT_NODE_FROM_OSF = 'preprint_contributor_added_preprint_node_from_osf'

        # Collections Submission notifications
        COLLECTION_SUBMISSION_REMOVED_ADMIN = 'collection_submission_removed_admin'
        COLLECTION_SUBMISSION_REMOVED_MODERATOR = 'collection_submission_removed_moderator'
        COLLECTION_SUBMISSION_REMOVED_PRIVATE = 'collection_submission_removed_private'
        COLLECTION_SUBMISSION_SUBMITTED = 'collection_submission_submitted'
        COLLECTION_SUBMISSION_ACCEPTED = 'collection_submission_accepted'
        COLLECTION_SUBMISSION_REJECTED = 'collection_submission_rejected'
        COLLECTION_SUBMISSION_CANCEL = 'collection_submission_cancel'

        # Schema Response notifications
        SCHEMA_RESPONSE_REJECTED = 'schema_response_rejected'
        SCHEMA_RESPONSE_APPROVED = 'schema_response_approved'
        SCHEMA_RESPONSE_SUBMITTED = 'schema_response_submitted'
        SCHEMA_RESPONSE_INITIATED = 'schema_response_initiated'

        REGISTRATION_BULK_UPLOAD_FAILURE_DUPLICATES = 'registration_bulk_upload_failure_duplicates'
        FILE_OPERATION_FAILED = 'file_operation_failed'
        FILE_OPERATION_SUCCESS = 'file_operation_success'

        @property
        def instance(self):
            obj, created = NotificationType.objects.get_or_create(name=self.value)
            return obj

        @classmethod
        def user_types(cls):
            return [member for member in cls if member.name.startswith('USER_')]

        @classmethod
        def node_types(cls):
            return [member for member in cls if member.name.startswith('NODE_')]

        @classmethod
        def preprint_types(cls):
            return [member for member in cls if member.name.startswith('PREPRINT_')]

        @classmethod
        def provider_types(cls):
            return [member for member in cls if member.name.startswith('PROVIDER_')]

        @classmethod
        def schema_response_types(cls):
            return [member for member in cls if member.name.startswith('SCHEMA_RESPONSE_')]

        @classmethod
        def desk_types(cls):
            return [member for member in cls if member.name.startswith('DESK_')]

    notification_interval_choices = ArrayField(
        base_field=models.CharField(max_length=32),
        default=get_default_frequency_choices,
        blank=True
    )

    name: str = models.CharField(max_length=255, unique=True, null=False, blank=False)

    object_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='Content type for subscribed objects. Null means global event.'
    )

    template: str = models.TextField(
        help_text='Template used to render the event_info. Supports Django template syntax.'
    )
    subject: str = models.TextField(
        blank=True,
        null=True,
        help_text='Template used to render the subject line of email. Supports Django template syntax.'
    )

    def emit(self, user, subscribed_object=None, message_frequency=None, event_context=None):
        """Emit a notification to a user by creating Notification and NotificationSubscription objects.

        Args:
            user (OSFUser): The recipient of the notification.
            subscribed_object (optional): The object the subscription is related to.
            event_context (dict, optional): Context for rendering the notification template.
        """
        from osf.models.notification_subscription import NotificationSubscription
        subscription, created = NotificationSubscription.objects.get_or_create(
            notification_type=self,
            user=user,
            content_type=ContentType.objects.get_for_model(subscribed_object) if subscribed_object else None,
            object_id=subscribed_object.pk if subscribed_object else None,
            defaults={'message_frequency': message_frequency},
        )
        if subscription.message_frequency == 'instantly':
            Notification.objects.create(
                subscription=subscription,
                event_context=event_context
            ).send()

    def add_user_to_subscription(self, user, *args, **kwargs):
        """
        """
        from osf.models.notification_subscription import NotificationSubscription

        provider = kwargs.pop('provider', None)
        node = kwargs.pop('node', None)
        data = {}
        if subscribed_object := provider or node:
            data = {
                'object_id': subscribed_object.id,
                'content_type_id': ContentType.objects.get_for_model(subscribed_object).id,
            }

        notification, created = NotificationSubscription.objects.get_or_create(
            user=user,
            notification_type=self,
            **data,
        )
        return notification

    def remove_user_from_subscription(self, user):
        """
        """
        from osf.models.notification_subscription import NotificationSubscription
        notification, _ = NotificationSubscription.objects.update_or_create(
            user=user,
            notification_type=self,
            defaults={'message_frequency': FrequencyChoices.NONE.value}
        )

    def __str__(self) -> str:
        return self.name

    class Meta:
        verbose_name = 'Notification Type'
        verbose_name_plural = 'Notification Types'
