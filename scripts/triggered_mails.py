import logging
import uuid

from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q, Exists, OuterRef
from django.utils import timezone

from framework.celery_tasks import app as celery_app
from osf.models import OSFUser
from website.app import init_app
from website import settings

from osf.models import EmailTask  # <-- new

from scripts.utils import add_file_logger

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

NO_LOGIN_PREFIX = 'no_login:'  # used to namespace this email type in task_id


def main(dry_run: bool = True):
    users = find_inactive_users_without_enqueued_or_sent_no_login()
    if not users.exists():
        logger.info('No users matched inactivity criteria.')
        return

    for user in users.iterator():
        if dry_run:
            logger.warning('Dry run mode')
            logger.warning(f'[DRY RUN] Would enqueue no_login email for {user.username}')
            continue

        with transaction.atomic():
            # Create the EmailTask row first (status=PENDING)
            task_id = f'{NO_LOGIN_PREFIX}{uuid.uuid4()}'
            email_task = EmailTask.objects.create(
                task_id=task_id,
                user=user,
                status='PENDING',
            )
            logger.info(f'Queued EmailTask {email_task.task_id} for user {user.username}')

            # Kick off the Celery task with the EmailTask PK
            send_no_login_email.delay(email_task_id=email_task.id)


def find_inactive_users_without_enqueued_or_sent_no_login():
    """
    Match your original inactivity rules, but exclude users who already have a no_login EmailTask
    either pending, started, retrying, or already sent successfully.
    """

    # Subquery: Is there already a not-yet-failed/aborted EmailTask for this user with our prefix?
    existing_no_login = EmailTask.objects.filter(
        user_id=OuterRef('pk'),
        task_id__startswith=NO_LOGIN_PREFIX,
        status__in=['PENDING', 'STARTED', 'RETRY', 'SUCCESS'],
    )

    base_q = OSFUser.objects.filter(is_active=True).filter(
        Q(
            date_last_login__lt=timezone.now() - settings.NO_LOGIN_WAIT_TIME,
            # NOT tagged osf4m
        ) & ~Q(tags__name='osf4m')
        |
        Q(
            date_last_login__lt=timezone.now() - settings.NO_LOGIN_OSF4M_WAIT_TIME,
            tags__name='osf4m'
        )
    )

    # Exclude users who already have a task for this email type
    return base_q.annotate(_has_task=Exists(existing_no_login)).filter(_has_task=False)


@celery_app.task(name='scripts.triggered_no_login_email')
def send_no_login_email(email_task_id: int):
    """
    Worker that sends the no-login email and updates EmailTask.status accordingly.
    """

    # Late import to avoid app registry issues in Celery
    from osf.models import EmailTask

    try:
        email_task = EmailTask.objects.select_related('user').get(id=email_task_id)
    except EmailTask.DoesNotExist:
        logger.error(f'EmailTask {email_task_id} not found')
        return

    # If this task already reached a terminal state, don't send again (idempotent)
    if email_task.status in ['SUCCESS']:
        logger.info(f'EmailTask {email_task.id} already SUCCESS; skipping')
        return

    # Update to STARTED
    EmailTask.objects.filter(id=email_task.id).update(status='STARTED')

    try:
        user = email_task.user
        if user is None:
            EmailTask.objects.filter(id=email_task.id).update(status='NO_USER_FOUND')
            logger.warning(f'EmailTask {email_task.id}: no associated user')
            return

        if not user.is_active:
            EmailTask.objects.filter(id=email_task.id).update(status='USER_DISABLED')
            logger.warning(f'EmailTask {email_task.id}: user {user.id} is not active')
            return

        # --- Send the email ---
        # Replace this with your real templated email system if desired.
        subject = 'We miss you at OSF'
        message = (
            f'Hello {user.fullname},\n\n'
            'We noticed you haven’t logged into OSF in a while. '
            'Your projects, registrations, and files are still here whenever you need them.\n\n'
            f'If you need help, contact us at {settings.OSF_SUPPORT_EMAIL}.\n\n'
            '— OSF Team'
        )
        from_email = settings.OSF_SUPPORT_EMAIL
        recipient_list = [user.username]  # assuming username is the email address

        # If you want HTML email or a template, swap in EmailMultiAlternatives and render_to_string.
        sent_count = send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=recipient_list,
            fail_silently=False,
        )

        if sent_count > 0:
            EmailTask.objects.filter(id=email_task.id).update(status='SUCCESS')
            logger.info(f'EmailTask {email_task.id}: email sent to {user.username}')
        else:
            EmailTask.objects.filter(id=email_task.id).update(
                status='FAILURE',
                error_message='send_mail returned 0'
            )
            logger.error(f'EmailTask {email_task.id}: send_mail returned 0')

    except Exception as exc:  # noqa: BLE001
        logger.exception(f'EmailTask {email_task.id}: error while sending')
        EmailTask.objects.filter(id=email_task.id).update(
            status='FAILURE',
            error_message=str(exc)
        )


@celery_app.task(name='scripts.triggered_mails')  # keep the original entry point for compatibility
def run_main(dry_run=True):
    init_app(routes=False)
    if not dry_run:
        add_file_logger(logger, __file__)
    main(dry_run=dry_run)
