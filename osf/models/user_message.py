from typing import Type
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from . import NotificationType
from .base import BaseModel, ObjectIDMixin


class MessageTypes(models.TextChoices):
    """
    Enumeration of the different user-to-user message types supported by UserMessage.

    Notes:
        Message types should be limited to direct communication between two users.
        These may include cases where the sender represents an organization or group,
        but they must not involve bulk messaging or group-wide notifications.
    """
    # Admin-to-member communication within an institution.
    INSTITUTIONAL_REQUEST = ('institutional_request', 'INSTITUTIONAL_REQUEST')

    @classmethod
    def get_template(cls: Type['MessageTypes'], message_type: str) -> str:
        """
        Retrieve the email template associated with a specific message type.

        Args:
            message_type (str): The type of the message.

        Returns:
            str: The email template string for the specified message type.
        """
        return {
            cls.INSTITUTIONAL_REQUEST: NotificationType.Type.NODE_INSTITUTIONAL_ACCESS_REQUEST
        }[message_type]


class UserMessage(BaseModel, ObjectIDMixin):
    """
    Represents a user-to-user message, potentially sent on behalf of an organization or group.

    Attributes:
        sender (OSFUser): The user who initiated the message.
        recipient (OSFUser): The intended recipient of the message.
        message_text (str): The content of the message being sent.
        message_type (str): The type of message, e.g., 'institutional_request'.
        institution (Institution): The institution linked to the message, if applicable.
    """
    sender = models.ForeignKey(
        'OSFUser',
        on_delete=models.CASCADE,
        related_name='sent_user_messages',
        help_text='The user who sent this message.'
    )
    recipient = models.ForeignKey(
        'OSFUser',
        on_delete=models.CASCADE,
        related_name='received_user_messages',
        help_text='The recipient of this message.'
    )
    message_text = models.TextField(
        help_text='The content of the message. The custom text of a formatted email.'
    )
    message_type = models.CharField(
        max_length=50,
        choices=MessageTypes.choices,
        help_text='The type of message being sent, as defined in MessageTypes.'
    )
    institution = models.ForeignKey(
        'Institution',
        on_delete=models.CASCADE,
        help_text='The institution associated with this message.'
    )
    is_sender_BCCed = models.BooleanField(
        default=False,
        help_text='The boolean value that indicates whether other institutional admins were BCCed',
    )
    reply_to = models.BooleanField(
        default=False,
        help_text='Whether to set the sender\'s username as the `Reply-To` header in the email.'
    )

    def send_institution_request(self) -> None:
        """
        Sends an institutional access request email to the recipient of the message.
        """
        NotificationType.objects.get(
            name=MessageTypes.get_template(self.message_type)
        ).emit(
            user=self.recipient,
            event_context={
                'sender': self.sender,
                'recipient': self.recipient,
                'message_text': self.message_text,
                'institution': self.institution,
            },
            email_context={
                'bcc_addr': [self.sender.username] if self.is_sender_BCCed else None,
                'reply_to': self.sender.username if self.reply_to else None,
            }
        )


@receiver(post_save, sender=UserMessage)
def user_message_created(sender: Type[UserMessage], instance: UserMessage, created: bool, **kwargs) -> None:
    """
    Signal handler executed after a UserMessage instance is saved.

    Args:
        sender (Type[UserMessage]): The UserMessage model class.
        instance (UserMessage): The newly created instance of the UserMessage.
        created (bool): Whether this is the first save of the instance.

    Notes:
        If the message type is 'INSTITUTIONAL_REQUEST', it triggers sending an
        institutional request email. Raises an error for unsupported message types.
    """
    if not created:
        return  # Ignore subsequent saves.

    if instance.message_type == MessageTypes.INSTITUTIONAL_REQUEST:
        instance.send_institution_request()
    else:
        raise NotImplementedError(f'Unsupported message type: {instance.message_type}')
