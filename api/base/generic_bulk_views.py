
from rest_framework import status
from rest_framework.response import Response
from rest_framework_bulk import generics as bulk_generics
from rest_framework.exceptions import PermissionDenied, ValidationError, ParseError

from framework.auth.core import Auth

from website.project.model import Q
from api.base.settings import BULK_SETTINGS
from api.base.exceptions import Conflict, JSONAPIException
from api.base.utils import is_bulk_request


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
        if is_bulk_request(request):
            if not request.data:
                raise ValidationError('Request must contain array of resource identifier objects.')

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
        if not request.data:
            raise ValidationError('Request must contain array of resource identifier objects.')

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
        model_cls = request.parser_context['view'].model_class
        object_type = self.serializer_class.Meta.type_

        if not request.data:
            raise ValidationError('Request must contain array of resource identifier objects.')

        requested_ids = [data['id'] for data in request.data]
        resource_object_list = model_cls.find(Q('_id', 'in', requested_ids))

        if len(resource_object_list) != len(request.data):
            raise ValidationError({'non_field_errors': 'Could not find all objects to delete.'})

        for item in request.data:
            item_type = item[u'type']
            if item_type != object_type:
                raise Conflict()

        if 'node_id' not in kwargs:
            for resource_object in resource_object_list:
                if not resource_object.can_edit(Auth(user)):
                    raise PermissionDenied

        self.perform_bulk_destroy(resource_object_list)

        return Response(status=status.HTTP_204_NO_CONTENT)
