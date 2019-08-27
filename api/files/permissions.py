from rest_framework import permissions

from api.base.utils import get_user_auth
from osf.models import BaseFileNode, FileMetadataRecord
from api.preprints.permissions import PreprintPublishedOrAdmin
from osf.utils.permissions import ADMIN
from osf.utils.workflows import DefaultStates

class CheckedOutOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, BaseFileNode), 'obj must be a BaseFileNode, got {}'.format(obj)

        if request.method in permissions.SAFE_METHODS:
            return True

        auth = get_user_auth(request)
        # Limited to osfstorage for the moment
        if obj.provider != 'osfstorage':
            return False
        return obj.checkout is None \
            or obj.checkout == auth.user \
            or obj.target.has_permission(auth.user, ADMIN)


class IsPreprintFile(PreprintPublishedOrAdmin):
    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, BaseFileNode), 'obj must be a BaseFileNode, got {}'.format(obj)
        if (hasattr(obj.target, 'primary_file') and obj.target.primary_file == obj):
            if request.method == 'DELETE' and obj.target.machine_state != DefaultStates.INITIAL.value:
                return False

            if obj.target.is_retracted and request.method in permissions.SAFE_METHODS:
                return obj.target.can_view_files(get_user_auth(request))

            # If object is a primary_file on a preprint, need PreprintPublishedOrAdmin permissions to view
            return super(IsPreprintFile, self).has_object_permission(request, view, obj.target)

        return True


def FileMetadataRecordPermission(Base):
    """
    Checks for the given base permission on the FileNode if the object is a file,
    or on the file metadata record's file target if it's a FileMetadataRecord.
    Leave it to the permission being wrapped to enforce acceptable_models for obj.
    """
    class Perm(Base):
        def get_object(self, request, view, obj):
            if isinstance(obj, BaseFileNode):
                return obj.target
            elif isinstance(obj, FileMetadataRecord):
                return obj.file.target
            return obj

        def has_object_permission(self, request, view, obj):
            obj = self.get_object(request, view, obj)
            return super(Perm, self).has_object_permission(request, view, obj)
    return Perm
