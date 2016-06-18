from django.utils import six
from collections import OrderedDict
from django.core.urlresolvers import reverse
from django.core.paginator import InvalidPage, Paginator as DjangoPaginator

from rest_framework import pagination
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.utils.urls import (
    replace_query_param, remove_query_param
)
from api.base.serializers import is_anonymized
from api.base.settings import MAX_PAGE_SIZE

from framework.guid.model import Guid
from website.project.model import Node, Comment


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

    def get_response_dict(self, data, url):
        return OrderedDict([
            ('data', data),
            ('links', OrderedDict([
                ('first', self.get_first_real_link(url)),
                ('last', self.get_last_real_link(url)),
                ('prev', self.get_previous_real_link(url)),
                ('next', self.get_next_real_link(url)),
                ('meta', OrderedDict([
                    ('total', self.page.paginator.count),
                    ('per_page', self.page.paginator.per_page),
                ]))
            ])),
        ])

    def get_paginated_response(self, data):
        """
        Formats paginated response in accordance with JSON API.

        Creates pagination links from the view_name if embedded resource,
        rather than the location used in the request.
        """
        kwargs = self.request.parser_context['kwargs'].copy()
        embedded = kwargs.pop('is_embedded', None)
        view_name = self.request.parser_context['view'].view_fqn
        reversed_url = None
        if embedded:
            reversed_url = reverse(view_name, kwargs=kwargs)

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
            paginator = DjangoPaginator(queryset, self.page_size)
            page_number = 1
            try:
                self.page = paginator.page(page_number)
            except InvalidPage as exc:
                msg = self.invalid_page_message.format(
                    page_number=page_number, message=six.text_type(exc)
                )
                raise NotFound(msg)

            if paginator.count > 1 and self.template is not None:
                # The browsable API should display pagination controls.
                self.display_page_controls = True

            self.request = request
            return list(self.page)

        else:
            return super(JSONAPIPagination, self).paginate_queryset(queryset, request, view=None)


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
            node = Node.load(node_id)
            user = self.request.user
            if target_id and not user.is_anonymous() and node.is_contributor(user):
                root_target = Guid.load(target_id)
                if root_target:
                    page = getattr(root_target.referent, 'root_target_page', None)
                    if page:
                        if not len(data):
                            unread = 0
                        else:
                            unread = Comment.find_n_unread(user=user, node=node, page=page, root_id=target_id)
                        response_dict['links']['meta']['unread'] = unread
        return Response(response_dict)


class NodeContributorPagination(JSONAPIPagination):

    def get_paginated_response(self, data):
        """ Add number of bibliographic contributors to links.meta"""
        response = super(NodeContributorPagination, self).get_paginated_response(data)
        response_dict = response.data
        kwargs = self.request.parser_context['kwargs'].copy()
        node_id = kwargs.get('node_id', None)
        node = Node.load(node_id)
        total_bibliographic = len(node.visible_contributor_ids)
        response_dict['links']['meta']['total_bibliographic'] = total_bibliographic
        return Response(response_dict)
