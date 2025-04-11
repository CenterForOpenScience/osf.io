"""Basic Event handling for events that need subscriptions"""
event_registry = {}


def register(event_type):
    """Register classes into event_registry"""
    def decorator(cls):
        event_registry[event_type] = cls
        return cls
    return decorator


class RegistryError(TypeError):
    pass
