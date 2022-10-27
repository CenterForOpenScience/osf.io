import osf.models as osfdb


def GuidReferentPermission(InnerPermission):
    """
    Checks for the given permission on the object's referent (if a Guid)
    or its guid's referent (if a GuidMetadataRecord).
    Leave it to the permission being wrapped to enforce acceptable_models for obj.
    """
    class Perm(InnerPermission):
        def has_object_permission(self, request, view, obj):
            if isinstance(obj, osfdb.Guid):
                obj = obj.referent
            elif isinstance(obj, osfdb.GuidMetadataRecord):
                obj = obj.guid.referent
            return super().has_object_permission(request, view, obj)
    return Perm
