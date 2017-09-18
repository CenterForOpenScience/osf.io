class InvalidTriggerError(Exception):
    def __init__(self, trigger, state, valid_triggers):
        self.trigger = trigger
        self.state = state
        self.valid_triggers = valid_triggers
        self.message = 'Cannot trigger "{}" from state "{}". Valid triggers: {}'.format(trigger, state, valid_triggers)
