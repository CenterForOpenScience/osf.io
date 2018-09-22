from django.utils import six
from collections import OrderedDict
from django.core.urlresolvers import reverse
from django.core.paginator import InvalidPage, Paginator as DjangoPaginator
from django.db.models import QuerySet

from rest_framework import pagination
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.utils.urls import (
    replace_query_param, remove_query_param,
)
from api.base.serializers import is_anonymized
from api.base.settings import MAX_PAGE_SIZE
from api.base.utils import absolute_reverse

from osf.models import AbstractNode, Comment, Preprint, Guid
from website.search.elastic_search import DOC_TYPE_TO_MODEL


class JSONAPIPagination(pagination.PageNumberPagination):
    """
    Custom paginator that formats responses in a JSON-API compatible format.

    Properly handles pagination of embedded objects.

    """

    page_size_query_param = 'page[size]'
    max_page_size = MAX_PAGE_SIZE

    def page_number_query(self, url, page_number):
        """
        Builds uri and adds page param.
        """
        url = remove_query_param(self.request.build_absolute_uri(url), '_')
        paginated_url = replace_query_param(url, self.page_query_param, page_number)

        if page_number == 1:
            return remove_query_param(paginated_url, self.page_query_param)

        return paginated_url

    def get_self_real_link(self, url):
        page_number = self.page.number
        return self.page_number_query(url, page_number)

    def get_first_real_link(self, url):
        if not self.page.has_previous():
            return None
        return self.page_number_query(url, 1)

    def get_last_real_link(self, url):
        if not self.page.has_next():
            return None
        page_number = self.page.paginator.num_pages
        return self.page_number_query(url, page_number)

    def get_previous_real_link(self, url):
        if not self.page.has_previous():
            return None
        page_number = self.page.previous_page_number()
        return self.page_number_query(url, page_number)

    def get_next_real_link(self, url):
        if not self.page.has_next():
            return None
        page_number = self.page.next_page_number()
        return self.page_number_query(url, page_number)

    def get_response_dict_deprecated(self, data, url):
        return OrderedDict([
            ('data', data),
            (
                'links', OrderedDict([
                    ('first', self.get_first_real_link(url)),
                    ('last', self.get_last_real_link(url)),
                    ('prev', self.get_previous_real_link(url)),
                    ('next', self.get_next_real_link(url)),
                    (
                        'meta', OrderedDict([
                            ('total', self.page.paginator.count),
                            ('per_page', self.page.paginator.per_page),
                        ]),
                    ),
                ]),
            ),
        ])

    def get_response_dict(self, data, url):
        return OrderedDict([
            ('data', data),
            (
                'meta', OrderedDict([
                    ('total', self.page.paginator.count),
                    ('per_page', self.page.paginator.per_page),
                ]),
            ),
            (
                'links', OrderedDict([
                    ('self', self.get_self_real_link(url)),
                    ('first', self.get_first_real_link(url)),
                    ('last', self.get_last_real_link(url)),
                    ('prev', self.get_previous_real_link(url)),
                    ('next', self.get_next_real_link(url)),
                ]),
            ),
        ])

    def get_paginated_response(self, data):
        """
        Formats paginated response in accordance with JSON API, as of version 2.1.
        Version 2.0 uses the response_dict_deprecated function,
        which does not return JSON API compliant pagination links.

        Creates pagination links from the view_name if embedded resource,
        rather than the location used in the request.
        """
        kwargs = self.request.parser_context['kwargs'].copy()
        embedded = kwargs.pop('is_embedded', None)
        view_name = self.request.parser_context['view'].view_fqn
        reversed_url = None
        if embedded:
            reversed_url = reverse(view_name, kwargs=kwargs)

        if self.request.version < '2.1':
            response_dict = self.get_response_dict_deprecated(data, reversed_url)
        else:
            response_dict = self.get_response_dict(data, reversed_url)

        if is_anonymized(self.request):
            if response_dict.get('meta', False):
                response_dict['meta'].update({'anonymous': True})
            else:
                response_dict['meta'] = {'anonymous': True}
        return Response(response_dict)

    def paginate_queryset(self, queryset, request, view=None):
        """
        Custom pagination of queryset. Returns page object or `None` if not configured for view.

        If this is an embedded resource, returns first page, ignoring query params.
        """
        if request.parser_context['kwargs'].get('is_embedded'):
            # Pagination requires an order by clause, especially when using Postgres.
            # see: https://docs.djangoproject.com/en/1.10/topics/pagination/#required-arguments
            if isinstance(queryset, QuerySet) and not queryset.ordered:
                queryset = queryset.order_by(queryset.model._meta.pk.name)

            paginator = DjangoPaginator(queryset, self.page_size)
            page_number = 1
            try:
                self.page = paginator.page(page_number)
            except InvalidPage as exc:
                msg = self.invalid_page_message.format(
                    page_number=page_number, message=six.text_type(exc),
                )
                raise NotFound(msg)

            if paginator.count > 1 and self.template is not None:
                # The browsable API should display pagination controls.
                self.display_page_controls = True

            self.request = request
            return list(self.page)

        else:
            return super(JSONAPIPagination, self).paginate_queryset(queryset, request, view=None)


class MaxSizePagination(JSONAPIPagination):
    page_size = 1000
    max_page_size = None
    page_size_query_param = None

class NoMaxPageSizePagination(JSONAPIPagination):
    max_page_size = None

class IncreasedPageSizePagination(JSONAPIPagination):
    max_page_size = 1000

class CommentPagination(JSONAPIPagination):

    def get_paginated_response(self, data):
        """Add number of unread comments to links.meta when viewing list of comments filtered by
        a target node, file or wiki page."""
        response = super(CommentPagination, self).get_paginated_response(data)
        response_dict = response.data
        kwargs = self.request.parser_context['kwargs'].copy()

        if self.request.query_params.get('related_counts', False):
            target_id = self.request.query_params.get('filter[target]', None)
            node_id = kwargs.get('node_id', None)
            node = AbstractNode.load(node_id)
            user = self.request.user
            if target_id and not user.is_anonymous and node.is_contributor(user):
                root_target = Guid.load(target_id)
                if root_target:
                    page = getattr(root_target.referent, 'root_target_page', None)
                    if page:
                        if not len(data):
                            unread = 0
                        else:
                            unread = Comment.find_n_unread(user=user, node=node, page=page, root_id=target_id)
                        if self.request.version < '2.1':
                            response_dict['links']['meta']['unread'] = unread
                        else:
                            response_dict['meta']['unread'] = unread
        return Response(response_dict)


class NodeContributorPagination(JSONAPIPagination):

    def get_resource(self, kwargs):
        resource_id = kwargs.get('node_id', None)
        return AbstractNode.load(resource_id)

    def get_paginated_response(self, data):
        """ Add number of bibliographic contributors to links.meta"""
        response = super(NodeContributorPagination, self).get_paginated_response(data)
        response_dict = response.data
        kwargs = self.request.parser_context['kwargs'].copy()
        node = self.get_resource(kwargs)
        total_bibliographic = node.visible_contributors.count()
        if self.request.version < '2.1':
            response_dict['links']['meta']['total_bibliographic'] = total_bibliographic
        else:
            response_dict['meta']['total_bibliographic'] = total_bibliographic
        return Response(response_dict)


class PreprintContributorPagination(NodeContributorPagination):

    def get_resource(self, kwargs):
        resource_id = kwargs.get('preprint_id')
        return Preprint.load(resource_id)


class SearchPaginator(DjangoPaginator):

    def __init__(self, object_list, per_page):
        super(SearchPaginator, self).__init__(object_list, per_page)

    def search_type_to_model(self, obj_id, obj_type):
        model = DOC_TYPE_TO_MODEL[obj_type]
        return model.load(obj_id)

    def _get_count(self):
        self._count = self.object_list['aggs']['total']
        return self._count
    count = property(_get_count)

    def page(self, number):
        number = self.validate_number(number)
        results = self.object_list['results']
        items = [
            self.search_type_to_model(result.get('_id'), result.get('_type'))
            for result in results
        ]
        return self._get_page(items, number, self)


class SearchModelPaginator(SearchPaginator):

    def __init__(self, object_list, per_page, model):
        super(SearchModelPaginator, self).__init__(object_list, per_page)
        self.model = model

    def page(self, number):
        number = self.validate_number(number)
        results = self.object_list['results']
        items = [
            self.model.load(result.get('_id'))
            for result in results
        ]
        return self._get_page(items, number, self)


class SearchPagination(JSONAPIPagination):

    def __init__(self):
        super(SearchPagination, self).__init__()
        self.paginator = None

    def paginate_queryset(self, queryset, request, view=None):
        page_size = self.get_page_size(request)
        if not page_size:
            return None

        # Pagination requires an order by clause, especially when using Postgres.
        # see: https://docs.djangoproject.com/en/1.10/topics/pagination/#required-arguments
        if isinstance(queryset, QuerySet) and not queryset.ordered:
            queryset = queryset.order_by(queryset.model._meta.pk.name)

        self.paginator = SearchPaginator(queryset, page_size)
        model = getattr(request.parser_context['view'], 'model_class', None)
        if model:
            self.paginator = SearchModelPaginator(queryset, page_size, model)

        page_number = request.query_params.get(self.page_query_param, 1)
        if page_number in self.last_page_strings:
            page_number = self.paginator.num_pages

        try:
            self.page = self.paginator.page(page_number)
        except InvalidPage as exc:
            msg = self.invalid_page_message.format(
                page_number=page_number, message=six.text_type(exc),
            )
            raise NotFound(msg)

        if self.paginator.num_pages > 1 and self.template is not None:
            # The browsable API should display pagination controls.
            self.display_page_controls = True

        self.request = request
        return list(self.page)

    def get_search_field_url(self, field, query):
        view_name = 'search:search-{}'.format(field)
        return absolute_reverse(
            view_name,
            query_kwargs={
                'q': query,
            },
            kwargs={
                'version': self.request.parser_context['kwargs']['version'],
            },
        )

    def get_search_field_total(self, field):
        return self.paginator.object_list['counts'].get(field, 0)

    def get_search_field(self, field, query):
        return OrderedDict([
            (
                'related', OrderedDict([
                    ('href', self.get_search_field_url(field, query)),
                    (
                        'meta', OrderedDict([
                            ('total', self.get_search_field_total(field)),
                        ]),
                    ),
                ]),
            ),
        ])

    def get_response_dict(self, data, url):
        if isinstance(self.paginator, SearchModelPaginator):
            return super(SearchPagination, self).get_response_dict(data, url)
        else:
            query = self.request.query_params.get('q', '*')
            return OrderedDict([
                ('data', data),
                (
                    'search_fields', OrderedDict([
                        ('files', self.get_search_field('file', query)),
                        ('projects', self.get_search_field('project', query)),
                        ('components', self.get_search_field('component', query)),
                        ('registrations', self.get_search_field('registration', query)),
                        ('users', self.get_search_field('user', query)),
                        ('institutions', self.get_search_field('institution', query)),
                    ]),
                ),
                (
                    'meta', OrderedDict([
                        ('total', self.page.paginator.count),
                        ('per_page', self.page.paginator.per_page),
                    ]),
                ),
                (
                    'links', OrderedDict([
                        ('self', self.get_self_real_link(url)),
                        ('first', self.get_first_real_link(url)),
                        ('last', self.get_last_real_link(url)),
                        ('prev', self.get_previous_real_link(url)),
                        ('next', self.get_next_real_link(url)),
                    ]),
                ),
            ])

    def get_response_dict_deprecated(self, data, url):
        if isinstance(self.paginator, SearchModelPaginator):
            return super(SearchPagination, self).get_response_dict_deprecated(data, url)
        else:
            query = self.request.query_params.get('q', '*')
            return OrderedDict([
                ('data', data),
                (
                    'search_fields', OrderedDict([
                        ('files', self.get_search_field('file', query)),
                        ('projects', self.get_search_field('project', query)),
                        ('components', self.get_search_field('component', query)),
                        ('registrations', self.get_search_field('registration', query)),
                        ('users', self.get_search_field('user', query)),
                        ('institutions', self.get_search_field('institution', query)),
                    ]),
                ),
                (
                    'links', OrderedDict([
                        ('first', self.get_first_real_link(url)),
                        ('last', self.get_last_real_link(url)),
                        ('prev', self.get_previous_real_link(url)),
                        ('next', self.get_next_real_link(url)),
                        (
                            'meta', OrderedDict([
                                ('total', self.page.paginator.count),
                                ('per_page', self.page.paginator.per_page),
                            ]),
                        ),
                    ]),
                ),
            ])
