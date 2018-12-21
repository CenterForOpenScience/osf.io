from django.contrib.admin.models import LogEntry, LogEntryManager

UNKNOWN = 0
ACCEPT_PREREG = 10
REJECT_PREREG = 11
COMMENT_PREREG = 12
CHECKOUT_CHECKUP = 13

CONFIRM_SPAM = 20
CONFIRM_HAM = 21

NODE_REMOVED = 30
NODE_RESTORED = 31
CONTRIBUTOR_REMOVED = 32
NODE_MADE_PRIVATE = 33

EMBARGO_UPDATED = 34

USER_REMOVED = 40
USER_RESTORED = 41
USER_2_FACTOR = 42
USER_EMAILED = 43

REINDEX_SHARE = 50
REINDEX_ELASTIC = 51

APPROVE_WITHDRAWAL = 60
REJECT_WITHDRAWAL = 61

PREPRINT_REMOVED = 70
PREPRINT_RESTORED = 71

def update_admin_log(user_id, object_id, object_repr, message, action_flag=UNKNOWN):
    AdminLogEntry.objects.log_action(
        user_id=user_id,
        content_type_id=None,
        object_id=object_id,
        object_repr=object_repr,
        change_message=message,
        action_flag=action_flag
    )


class AdminLogEntryManager(LogEntryManager):
    pass


class AdminLogEntry(LogEntry):
    primary_identifier_name = 'id'
    def message(self):
        return self.change_message
    message.allow_tags = True

    objects = AdminLogEntryManager()

    class Meta:
        proxy = True
