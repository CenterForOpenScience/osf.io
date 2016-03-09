from django.contrib.admin.models import LogEntry, CHANGE, LogEntryManager


def update_admin_log(user_id, object_id, object_repr, message, action_flag=CHANGE):
    try:
        OSFLogEntry.objects.log_action(
            user_id=user_id,
            content_type_id=None,
            object_id=object_id,
            object_repr=object_repr,
            change_message=message,
            action_flag=action_flag
        )
    except:
        print 'Failed to log changes to {}'.format(object_id)


class OSFLogEntryManager(LogEntryManager):
    pass


class OSFLogEntry(LogEntry):
    def message(self):
        return self.change_message
    message.allow_tags = True

    objects = OSFLogEntryManager()
