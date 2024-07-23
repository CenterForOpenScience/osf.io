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
        DefaultStates.INITIAL.value,
        DefaultStates.PENDING.value,
        DefaultStates.ACCEPTED.value,
        DefaultStates.REJECTED.value,
    ),
    Workflows.PRE_MODERATION.value: (
        DefaultStates.ACCEPTED.value,
    ),
    Workflows.POST_MODERATION.value: (
        DefaultStates.PENDING.value,
        DefaultStates.ACCEPTED.value,
    ),
}
