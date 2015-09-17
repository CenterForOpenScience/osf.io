def PermissionWithGetter(Base, getter):
    """A psuedo class for checking permissions
    of subresources without having to redefine permission classes
    """
    class Perm(Base):
        def get_object(self, request, view, obj):
            if callable(getter):
                return getter(request, view, obj)
            return getattr(obj, getter)

        def has_object_permission(self, request, view, obj):
            obj = self.get_object(request, view, obj)
            return super(Perm, self).has_object_permission(request, view, obj)
    return Perm
