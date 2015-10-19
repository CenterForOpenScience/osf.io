
from rest_framework import status
from rest_framework.response import Response
from rest_framework_bulk import generics as bulk_generics
from rest_framework.exceptions import PermissionDenied, ValidationError

from framework.auth.core import Auth

from api.base.utils import get_object_or_error
from api.base.settings import BULK_SETTINGS
from api.base.exceptions import Conflict, JSONAPIException
from api.base.utils import is_bulk_request

from website.project.model import Node


class ListBulkCreateJSONAPIView(bulk_generics.ListBulkCreateAPIView):
    """
    Custom ListBulkCreateAPIView that properly formats bulk create responses
    in accordance with the JSON API spec
    """

    # overrides ListBulkCreateAPIView
    def create(self, request, *args, **kwargs):
        """
        Correctly formats both bulk and single POST response
        """
        response = super(ListBulkCreateJSONAPIView, self).create(request, *args, **kwargs)
        if 'data' in response.data:
            return response
        return Response({'data': response.data}, status=status.HTTP_201_CREATED)

    # overrides ListBulkCreateAPIView
    def get_serializer(self, *args, **kwargs):
        """
        Adds many=True to serializer if bulk operation.
        """

        if is_bulk_request(self.request):
            kwargs['many'] = True

        return super(ListBulkCreateJSONAPIView, self).get_serializer(*args, **kwargs)


class BulkUpdateJSONAPIView(bulk_generics.BulkUpdateAPIView):
    """
    Custom BulkUpdateAPIView that properly formats bulk update responses in accordance with
    the JSON API spec
    """

    # overrides BulkUpdateAPIView
    def bulk_update(self, request, *args, **kwargs):
        """
        Correctly formats bulk PUT/PATCH response
        """
        response = super(BulkUpdateJSONAPIView, self).bulk_update(request, *args, **kwargs)
        return Response({'data': response.data}, status=status.HTTP_200_OK)


class BulkDestroyJSONAPIView(bulk_generics.BulkDestroyAPIView):
    """
    Custom BulkDestroyAPIView that handles validation and permissions for
    bulk delete
    """

    # Overrides BulkDestroyAPIView
    def bulk_destroy(self, request, *args, **kwargs):
        """
        Handles bulk destroy of resource objects.

        Handles some permissions, validation, and enforces bulk limit.
        """
        num_items = len(request.data)
        bulk_limit = BULK_SETTINGS['DEFAULT_BULK_LIMIT']

        if num_items > bulk_limit:
            raise JSONAPIException(source={'pointer': '/data'},
                                   detail='Bulk operation limit is {}, got {}.'.format(bulk_limit, num_items))

        user = self.request.user
        resource_object_list = []
        model_cls = kwargs['model']
        object_type = self.serializer_class.Meta.type_

        if not request.data:
            raise ValidationError('Request must contain array of resource identifier objects.')

        for item in request.data:
            item_type = item[u'type']
            if item_type != object_type:
                raise Conflict()

            resource_object = get_object_or_error(model_cls, item[u'id'])
            resource_object_list.append(resource_object)
            if model_cls is Node:
                if not resource_object.can_edit(Auth(user)):
                    raise PermissionDenied

        self.perform_bulk_destroy(resource_object_list)

        return Response(status=status.HTTP_204_NO_CONTENT)
