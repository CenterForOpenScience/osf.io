from rest_framework import status
from rest_framework.response import Response
from rest_framework_bulk import generics as bulk_generics
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.db.models import Q

from api.base.settings import BULK_SETTINGS
from api.base.exceptions import Conflict, JSONAPIException, Gone
from api.base.utils import is_bulk_request
from osf.models.base import GuidMixin


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
        if 'data' not in response.data:
            response.data = {'data': response.data}
        return response

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
        errors = {}
        if 'errors' in response.data[-1]:
            errors = response.data.pop(-1)
        response.data = {'data': response.data}
        if errors:
            response.data.update(errors)
        return response


class BulkDestroyJSONAPIView(bulk_generics.BulkDestroyAPIView):
    """
    Custom BulkDestroyAPIView that handles validation and permissions for
    bulk delete
    """
    def get_requested_resources(self, request, request_data):
        """
        Retrieves resources in request body
        """
        model_cls = request.parser_context['view'].model_class

        requested_ids = [data['id'] for data in request_data]
        column_name = 'guids___id' if issubclass(model_cls, GuidMixin) else getattr(model_cls, 'primary_identifier_name', '_id')
        resource_object_list = model_cls.objects.filter(Q(**{'{}__in'.format(column_name): requested_ids}))

        for resource in resource_object_list:
            if getattr(resource, 'is_deleted', None):
                raise Gone

        if len(resource_object_list) != len(request_data):
            raise ValidationError({'non_field_errors': 'Could not find all objects to delete.'})

        return [resource_object_list.get(**{column_name: id}) for id in requested_ids]

    def allow_bulk_destroy_resources(self, user, resource_list):
        """
        Ensures user has permission to bulk delete resources in request body. Override if not deleting relationships.
        """
        return True

    def bulk_destroy_skip_uneditable(self, resource_list, user, object_type):
        """
        Override on view if allowing bulk delete request to skip resources for which the user does not have permission
        to delete.  Method should return a dict in this format: {'skipped': [array of resources which should be skipped],
        'allowed': [array of resources which should be deleted]}
        """
        return None

    # Overrides BulkDestroyAPIView
    def bulk_destroy(self, request, *args, **kwargs):
        """
        Handles bulk destroy of resource objects.

        Handles some validation and enforces bulk limit.
        """
        if hasattr(request, 'query_params') and 'id' in request.query_params:
            if hasattr(request, 'data') and len(request.data) > 0:
                raise Conflict('A bulk DELETE can only have a body or query parameters, not both.')

            ids = request.query_params['id'].split(',')

            if 'type' in request.query_params:
                request_type = request.query_params['type']
                data = []
                for id in ids:
                    data.append({'type': request_type, 'id': id})
            else:
                raise ValidationError('Type query parameter is also required for a bulk DELETE using query parameters.')
        elif not request.data:
            raise ValidationError('Request must contain array of resource identifier objects.')
        else:
            data = request.data

        num_items = len(data)
        bulk_limit = BULK_SETTINGS['DEFAULT_BULK_LIMIT']

        if num_items > bulk_limit:
            raise JSONAPIException(source={'pointer': '/data'},
                                   detail='Bulk operation limit is {}, got {}.'.format(bulk_limit, num_items))

        user = self.request.user
        object_type = self.serializer_class.Meta.type_

        resource_object_list = self.get_requested_resources(request=request, request_data=data)

        for item in data:
            item_type = item[u'type']
            if item_type != object_type:
                raise Conflict('Type needs to match type expected at this endpoint.')

        if not self.allow_bulk_destroy_resources(user, resource_object_list):
            raise PermissionDenied

        skip_uneditable = self.bulk_destroy_skip_uneditable(resource_object_list, user, object_type)
        if skip_uneditable:
            skipped = skip_uneditable['skipped']
            allowed = skip_uneditable['allowed']
            if skipped:
                self.perform_bulk_destroy(allowed)
                return Response(status=status.HTTP_200_OK, data={'errors': skipped})

        self.perform_bulk_destroy(resource_object_list)
        return Response(status=status.HTTP_204_NO_CONTENT)
