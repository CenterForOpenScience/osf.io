from __future__ import unicode_literals

from enum import unique

from osf.utils.workflows import ChoiceEnum, DefaultStates


@unique
class Workflows(ChoiceEnum):
    NONE = None
    PRE_MODERATION = 'pre-moderation'  # moderation before approval
    POST_MODERATION = 'post-moderation'  # moderation after approval
    HYBRID_MODERATION = 'hybrid-moderation'  # moderation after approval moderator/admin, moderation before for everyone else


PUBLIC_STATES = {
    Workflows.NONE.value: (
        DefaultStates.INITIAL.db_name,
        DefaultStates.PENDING.db_name,
        DefaultStates.ACCEPTED.db_name,
        DefaultStates.REJECTED.db_name,
    ),
    Workflows.PRE_MODERATION.value: (
        DefaultStates.ACCEPTED.db_name,
    ),
    Workflows.POST_MODERATION.value: (
        DefaultStates.PENDING.db_name,
        DefaultStates.ACCEPTED.db_name,
    ),
}
