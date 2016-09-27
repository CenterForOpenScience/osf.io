from rest_framework import exceptions as drf_exceptions
from rest_framework import versioning as drf_versioning
from rest_framework.compat import unicode_http_header
from rest_framework.utils.mediatypes import _MediaType

from api.base import exceptions
from api.base import utils


def get_major_version(version):
    return int(version.split('.')[0])


def url_path_version_to_decimal(url_path_version):
    # 'v2' --> '2.0'
    return str(float(url_path_version.split('v')[1]))


def decimal_version_to_url_path(decimal_version):
    # '2.0' --> 'v2'
    return 'v{}'.format(get_major_version(decimal_version))


class BaseVersioning(drf_versioning.BaseVersioning):

    def __init__(self):
        super(BaseVersioning, self).__init__()

    def get_url_path_version(self, kwargs):
        invalid_version_message = 'Invalid version in URL path.'
        version = kwargs.get(self.version_param)
        version = url_path_version_to_decimal(version)
        if not self.is_allowed_version(version):
            raise drf_exceptions.NotFound(invalid_version_message)
        if get_major_version(version) == get_major_version(self.default_version):
            return self.default_version
        return version

    def get_header_version(self, request):
        invalid_version_message = 'Invalid version in "Accept" header.'
        media_type = _MediaType(request.accepted_media_type)
        version = media_type.params.get(self.version_param)
        if not version:
            return None
        version = unicode_http_header(version)
        if not self.is_allowed_version(version):
            raise drf_exceptions.NotAcceptable(invalid_version_message)
        return version

    def get_query_param_version(self, request):
        invalid_version_message = 'Invalid version in query parameter.'
        version = request.query_params.get(self.version_param)
        if not version:
            return None
        if not self.is_allowed_version(version):
            raise drf_exceptions.NotFound(invalid_version_message)
        return version

    def validate_pinned_versions(self, url_path_version, header_version, query_parameter_version):
        url_path_major_version = get_major_version(url_path_version)
        header_major_version = get_major_version(header_version) if header_version else None
        query_major_version = get_major_version(query_parameter_version) if query_parameter_version else None
        if header_version and header_major_version != url_path_major_version:
            raise exceptions.Conflict(
                detail='Version {} specified in "Accept" header does not fall within URL path version {}'.format(
                    header_version,
                    url_path_version
                )
            )
        if query_parameter_version and query_major_version != url_path_major_version:
            raise exceptions.Conflict(
                detail='Version {} specified in query parameter does not fall within URL path version {}'.format(
                    query_parameter_version,
                    url_path_version
                )
            )
        if header_version and query_parameter_version and (header_version != query_parameter_version):
            raise exceptions.Conflict(
                detail='Version {} specified in "Accept" header does not match version {} specified in query parameter'.format(
                    header_version,
                    query_parameter_version
                )
            )

    def determine_version(self, request, *args, **kwargs):
        header_version = self.get_header_version(request)
        url_path_version = self.get_url_path_version(kwargs)
        query_parameter_version = self.get_query_param_version(request)

        version = url_path_version
        if header_version or query_parameter_version:
            self.validate_pinned_versions(url_path_version, header_version, query_parameter_version)
            version = header_version if header_version else query_parameter_version

        return version

    def reverse(self, viewname, args=None, kwargs=None, request=None, format=None, **extra):
        url_path_version = self.get_url_path_version(kwargs)
        query_parameter_version = self.get_query_param_version(request)

        kwargs = {} if (kwargs is None) else kwargs
        kwargs[self.version_param] = decimal_version_to_url_path(url_path_version)
        query_kwargs = {'version': query_parameter_version} if query_parameter_version else None

        return utils.absolute_reverse(
            viewname, query_kwargs=query_kwargs, args=args, kwargs=kwargs
        )
