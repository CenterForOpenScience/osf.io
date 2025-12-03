"""
A property cache mechanism.
The cache is stored on the model as a protected attribute. Expensive
property lookups, such as database access, can therefore be sped up
when accessed multiple times in the same request.
The property can also be safely set and deleted without interference.

NOTE: Properties will *not* be cached if they return `None`. Use
`django.utils.functional.cached_property` for properties that
can return `None` and do not need a setter.
"""

from functools import wraps
import time

# from https://github.com/etianen/django-optimizations/blob/master/src/optimizations/propertycache.py


class _CachedProperty(property):
    """A property who's value is cached on the object."""

    def __init__(self, fget, fset=None, fdel=None, doc=None):
        """Initializes the cached property."""
        self._cache_name = '_{name}_cache'.format(
            name=fget.__name__,
        )
        # Wrap the accessors.
        fget = self._wrap_fget(fget)
        if callable(fset):
            fset = self._wrap_fset(fset)
        if callable(fdel):
            fdel = self._wrap_fdel(fdel)
        # Create the property.
        super().__init__(fget, fset, fdel, doc)

    def _wrap_fget(self, fget):
        @wraps(fget)
        def do_fget(obj):
            if hasattr(obj, self._cache_name):
                return getattr(obj, self._cache_name)
            # Generate the value to cache.
            value = fget(obj)
            if value:
                setattr(obj, self._cache_name, value)
            return value

        return do_fget

    def _wrap_fset(self, fset):
        @wraps(fset)
        def do_fset(obj, value):
            fset(obj, value)
            setattr(obj, self._cache_name, value)

        return do_fset

    def _wrap_fdel(self, fdel):
        @wraps(fdel)
        def do_fdel(obj):
            fdel(obj)
            delattr(obj, self._cache_name)

        return do_fdel


class _TTLCachedProperty(property):
    """A cached property with configurable TTL (time-to-live)."""

    def __init__(self, fget, fset=None, fdel=None, doc=None, ttl=None):
        self._cache_name = f"_{fget.__name__}_cache"
        self._cache_time_name = f"_{fget.__name__}_cache_time"
        self._ttl = ttl  # seconds or None (infinite)

        fget = self._wrap_fget(fget)
        if callable(fset):
            fset = self._wrap_fset(fset)
        if callable(fdel):
            fdel = self._wrap_fdel(fdel)

        super().__init__(fget, fset, fdel, doc)

    def _wrap_fget(self, fget):
        @wraps(fget)
        def do_fget(obj):
            if hasattr(obj, self._cache_name):
                # If TTL is set, validate expiration
                if self._ttl is not None:
                    cached_time = getattr(obj, self._cache_time_name, None)
                    if cached_time is not None:
                        if time.time() - cached_time < self._ttl:
                            return getattr(obj, self._cache_name)
                    # TTL expired
                    delattr(obj, self._cache_name)
                    if hasattr(obj, self._cache_time_name):
                        delattr(obj, self._cache_time_name)
                else:
                    return getattr(obj, self._cache_name)

            # Generate new value
            value = fget(obj)
            if value:
                setattr(obj, self._cache_name, value)
                setattr(obj, self._cache_time_name, time.time())
            return value

        return do_fget

    def _wrap_fset(self, fset):
        @wraps(fset)
        def do_fset(obj, value):
            fset(obj, value)
            setattr(obj, self._cache_name, value)
            setattr(obj, self._cache_time_name, time.time())

        return do_fset

    def _wrap_fdel(self, fdel):
        @wraps(fdel)
        def do_fdel(obj):
            fdel(obj)
            if hasattr(obj, self._cache_name):
                delattr(obj, self._cache_name)
            if hasattr(obj, self._cache_time_name):
                delattr(obj, self._cache_time_name)

        return do_fdel


# Public name for the cached property decorator. Using a class as a decorator just looks plain ugly. :P
cached_property = _CachedProperty

def ttl_cached_property(ttl=None):
    """Public decorator for TTL cached property."""
    def decorator(func):
        return _TTLCachedProperty(func, ttl=ttl)
    return decorator
