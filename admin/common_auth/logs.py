from django.contrib.admin.models import LogEntry, CHANGE, LogEntryManager

ACCEPT_PREREG = 10
REJECT_PREREG = 11
COMMENT_PREREG = 12

CONFIRM_SPAM = 20
CONFIRM_HAM = 21

NODE_REMOVED = 30
NODE_RESTORED = 31
CONTRIBUTOR_REMOVED = 32


def update_admin_log(user_id, object_id, object_repr, message, action_flag=CHANGE):
    OSFLogEntry.objects.log_action(
        user_id=user_id,
        content_type_id=None,
        object_id=object_id,
        object_repr=object_repr,
        change_message=message,
        action_flag=action_flag
    )


class OSFLogEntryManager(LogEntryManager):
    pass


class OSFLogEntry(LogEntry):
    def message(self):
        return self.change_message
    message.allow_tags = True

    objects = OSFLogEntryManager()
