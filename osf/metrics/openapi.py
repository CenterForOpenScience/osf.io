'''utilities for generating an openapi description of the metrics api

following https://spec.openapis.org/oas/v3.1.0

(the dataclasses might could be helpful in reuse, if extended to the whole openapi spec)
'''
import dataclasses
import enum
from collections.abc import Iterable
from http import HTTPStatus
from typing import Any

from website import settings as website_settings


class Mediatype(enum.Enum):
    JSONAPI = 'application/vnd.api+json'


def get_metrics_openapi_json_dict(reports: dict[str, type]) -> str:
    return get_metrics_openapi_root(reports).as_json_dict()


def get_metrics_openapi_root(reports: dict[str, type]) -> 'OpenapiRoot':
    # TODO: language parameter, get translations
    _parameters = get_metrics_openapi_parameters(reports)
    return OpenapiRoot(
        # 'externalDocs': {'url': TROVE.search_api},
        info=OpenapiInfo(
            title='osf:metrics reports api (unstable)',
            version='0.0.1',
            summary='View metrics reports and query metrics data',
            # description=  # TODO
            termsOfService='https://github.com/CenterForOpenScience/cos.io/blob/HEAD/TERMS_OF_USE.md',
            contact=OpenapiContact(email=website_settings.OSF_SUPPORT_EMAIL),
            # license=OpenapiLicense(...
        ),
        servers=[OpenapiServer(
            url=f'{website_settings.API_DOMAIN}_/metrics/',
        )],
        components={
            'parameters': _parameters,
        },
        paths=get_metrics_openapi_paths(_parameters),
    )


def get_metrics_openapi_paths(parameters) -> dict[str, 'OpenapiPath']:
    return {
        '/reports/': OpenapiPath({
            'get': OpenapiOperation(
                operationId='reports:index',
                summary='Reports: Index',
                description='Index of links to each available report type',
                responses=OpenapiResponses({
                    HTTPStatus.OK: OpenapiResponse(
                        description='Index of links to each available report type',
                        content={
                            Mediatype.JSONAPI: OpenapiMediatypeContent(
                                examples={
                                    'index': OpenapiExample(
                                        summary='reports index',
                                        externalValue=f'{website_settings.API_DOMAIN}_/metrics/reports/',
                                    ),
                                }
                            ),
                        },
                    ),
                }),
            ),
        }),

        '/reports/{report_type}/recent': OpenapiPath({
            'get': OpenapiOperation(
                operationId='reports:recent-list',
                summary='Reports: Recent',
                description='recent metrics reports of a given report type',
                responses=OpenapiResponses({
                    HTTPStatus.OK: OpenapiResponse(
                        description='list of reports matching the given type and timeframe',
                        content={
                            Mediatype.JSONAPI: OpenapiMediatypeContent(
                                examples={
                                    'user_summary_week': OpenapiExample(
                                        summary='user sessions per day over the past week',
                                        externalValue=f'{website_settings.API_DOMAIN}_/metrics/reports/user_summary/recent/',
                                    ),
                                },
                            ),
                        },
                    ),
                    HTTPStatus.NOT_FOUND: OpenapiResponse(
                        description='unknown report_type',
                    ),
                }),
            ),
        }, parameters=[
            parameters['report_type'].as_ref(),
            parameters['days_back'].as_ref(),
            parameters['timeframe'].as_ref(),
            parameters['timeframeStart'].as_ref(),
            parameters['timeframeEnd'].as_ref(),
        ]),

        '/query/node_analytics/{osfid}/{timespan}/': OpenapiPath(
            operations={
                'get': OpenapiOperation(
                    operationId='query:node-analytics',
                    summary='Query: Node Analytics',
                    description='a bespoke metrics query for the "node analytics" page',
                    responses=OpenapiResponses({
                        HTTPStatus.OK: OpenapiResponse(
                            description='list of recent metrics reports of a given report type',
                            content={
                                Mediatype.JSONAPI: OpenapiMediatypeContent(
                                    examples={
                                        'ezcuj_week': OpenapiExample(
                                            summary='usage info over the past week for https://osf.io/ezcuj',
                                            externalValue=f'{website_settings.API_DOMAIN}_/metrics/query/node_analytics/ezcuj/week/',
                                        )
                                    },
                                ),
                            },
                        ),
                        HTTPStatus.NOT_FOUND: OpenapiResponse(
                            description='unknown osfid',
                        ),
                        HTTPStatus.BAD_REQUEST: OpenapiResponse(
                            description='invalid timespan',
                        ),
                    }),
                ),
            },
            parameters=[
                parameters['osfid'].as_ref(),
                parameters['timespan'].as_ref(),
            ],
        ),

        '/query/user_visits/': OpenapiPath(
            operations={
                'get': OpenapiOperation(
                    operationId='query:user-visits',
                    summary='Query: Daily User Sessions',
                    description='a bespoke metrics query to support a histogram of user session counts over time (including anonymous sessions)',
                    responses=OpenapiResponses({
                        HTTPStatus.OK: OpenapiResponse(
                            description='user sessions per day over the given time range',
                            content={
                                Mediatype.JSONAPI: OpenapiMediatypeContent(
                                    examples={
                                        'relative_week': OpenapiExample(
                                            summary='user sessions per day over the past week',
                                            externalValue=f'{website_settings.API_DOMAIN}_/metrics/query/user_visits/?timeframe=previous_7_days',
                                        ),
                                        'absolute_week': OpenapiExample(
                                            summary='user sessions per day for the first week of February 2024',
                                            externalValue=f'{website_settings.API_DOMAIN}_/metrics/query/user_visits/?timeframeStart=2024-02-01&timeframeEnd=2024-02-08',
                                        ),
                                    },
                                ),
                            },
                        ),
                        HTTPStatus.BAD_REQUEST: OpenapiResponse(
                            description='bad parameter value(s)',
                        ),
                    }),
                ),
            },
            parameters=[
                parameters['timeframe'].as_ref(),
                parameters['timeframeStart'].as_ref(),
                parameters['timeframeEnd'].as_ref(),
            ],
        ),

        '/query/unique_user_visits/': OpenapiPath(
            operations={
                'get': OpenapiOperation(
                    operationId='query:unique-user-visits',
                    summary='Query: Daily Authenticated User Sessions',
                    description='a bespoke metrics query to support a histogram of authenticated user session counts over time',
                    responses=OpenapiResponses({
                        HTTPStatus.OK: OpenapiResponse(
                            description='user sessions per day over the given time range (NOT including anonymous sessions)',
                            content={
                                Mediatype.JSONAPI: OpenapiMediatypeContent(
                                    examples={
                                        'relative_week': OpenapiExample(
                                            summary='authenticated user sessions per day over the past week',
                                            externalValue=f'{website_settings.API_DOMAIN}_/metrics/query/unique_user_visits/?timeframe=previous_7_days',
                                        ),
                                        'absolute_week': OpenapiExample(
                                            summary='authenticated user sessions per day for the first week of February 2024',
                                            externalValue=f'{website_settings.API_DOMAIN}_/metrics/query/unique_user_visits/?timeframeStart=2024-02-01&timeframeEnd=2024-02-08',
                                        ),
                                    },
                                ),
                            },
                        ),
                        HTTPStatus.BAD_REQUEST: OpenapiResponse(
                            description='bad parameter value(s)',
                        ),
                    }),
                ),
            },
            parameters=[
                parameters['timeframe'].as_ref(),
                parameters['timeframeStart'].as_ref(),
                parameters['timeframeEnd'].as_ref(),
            ],
        ),
    }

def get_metrics_openapi_parameters(reports: dict[str, type]) -> dict:
    return {
        'days_back': OpenapiParameter(
            name='days_back',
            location=OpenapiParameterLocation.QUERY,
            required=False,
            deprecated=True,
            description='''
shorthand for a timeframe relative to the current date

(may not be used with `timeframe`, `timeframeStart`, or `timeframeEnd`)
            ''',
            schema={'type': 'integer', 'minimum': 1},
            example=1,
            examples={
                'fortnight': OpenapiExample(14),
                'year': OpenapiExample(365),
            },
        ),
        'timeframe': OpenapiParameter(
            name='timeframe',
            location=OpenapiParameterLocation.QUERY,
            required=False,
            description='''
shorthand for a timeframe relative to the current date

(may not be used with `timeframeStart` or `timeframeEnd`)
            ''',
            schema={
                'type': 'string',
                'pattern': r'previous_(\d+)_(day|month|year)s?',
            },
            example='previous_1_month',
            examples={
                'three_days': OpenapiExample('previous_3_days'),
                'two_months': OpenapiExample('previous_2_months'),
                'one_year': OpenapiExample('previous_1_year'),
            },
        ),
        'timeframeStart': OpenapiParameter(
            name='timeframeStart',
            location=OpenapiParameterLocation.QUERY,
            required=False,
            description='earliest date in a timeframe, YYYY-MM-DD',
            schema={
                'type': 'string',
                'pattern': r'\d{4}-\d{2}-\d{2}',
            },
            example='2024-01-01',
        ),
        'timeframeEnd': OpenapiParameter(
            name='timeframeEnd',
            location=OpenapiParameterLocation.QUERY,
            required=False,
            description='end date for a timeframe, YYYY-MM-DD (not included in the timeframe)',
            schema={
                'type': 'string',
                'pattern': r'\d{4}-\d{2}-\d{2}',
            },
            example='2024-01-01',
        ),
        'osfid': OpenapiParameter(
            name='osfid',
            location=OpenapiParameterLocation.PATH,
            required=True,
            description='the short "guid" for an osf node',
            schema={'type': 'string'},
            example='ezcuj',
        ),
        'timespan': OpenapiParameter(
            name='timespan',
            location=OpenapiParameterLocation.PATH,
            required=True,
            description='this query available for limited timespans, all relative to now',
            schema={'type': 'string', 'enum': ['day', 'week', 'fortnight']},
            example='week',
        ),
        'report_type': OpenapiParameter(
            name='report_type',
            location=OpenapiParameterLocation.PATH,
            required=True,
            description='type of report (controlled vocab)',
            schema={'type': 'string', 'enum': list(reports.keys())},
        ),
    }


###
# dataclasses and enums to ease building openapi docs

class JsonDataclass:
    def as_json_dict(self, skip_fields=None):
        _jsondict = {}
        for _field in dataclasses.fields(self):
            if (skip_fields is None) or (_field.name not in skip_fields):
                _field_value = getattr(self, _field.name)
                if _field_value is not None:
                    _jsondict[_field.name] = _make_jsonable(_field_value)
        return _jsondict


def _make_jsonable(value):
    if isinstance(value, (str, int)):
        return value
    if isinstance(value, (list, tuple)):
        return [
            _make_jsonable(_val)
            for _val in value
        ]
    if isinstance(value, dict):
        return {
            _make_jsonable(_key): _make_jsonable(_value)
            for _key, _value in value.items()
        }
    if isinstance(value, enum.Enum):
        return value.value
    try:
        return value.as_json_dict()
    except AttributeError:
        raise ValueError(f'what do with {value}')


@dataclasses.dataclass
class OpenapiExample(JsonDataclass):
    value: Any = None
    summary: str | None = None
    description: str | None = None
    externalValue: str | None = None


class OpenapiParameterLocation(enum.Enum):
    QUERY = 'query'
    HEADER = 'header'
    PATH = 'path'
    COOKIE = 'cookie'


@dataclasses.dataclass
class OpenapiParameter(JsonDataclass):
    name: str
    location: OpenapiParameterLocation
    description: str
    required: bool
    deprecated: bool = False
    allowEmptyValue: bool = False
    schema: dict | None = None
    example: Any = None
    examples: dict[str, OpenapiExample] | None = None

    def as_json_dict(self):
        _parameter_json = super().as_json_dict(skip_fields={'location'})
        _parameter_json['in'] = _make_jsonable(self.location)
        return _parameter_json

    def as_ref(self):
        return {'$ref': f'#/components/parameters/{self.name}'}


@dataclasses.dataclass
class OpenapiHeader(JsonDataclass):
    description: str
    required: bool
    deprecated: bool = False
    allowEmptyValue: bool = False
    schema: dict | None = None


@dataclasses.dataclass
class OpenapiMediatypeContent(JsonDataclass):
    example: Any = None
    schema: dict | None = None
    examples: dict[str, OpenapiExample] | None = None


@dataclasses.dataclass
class OpenapiResponse(JsonDataclass):
    description: str
    content: dict[Mediatype, OpenapiMediatypeContent] = dataclasses.field(default_factory=dict)
    headers: dict[str, OpenapiHeader] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class OpenapiResponses(JsonDataclass):
    by_status_code: dict[HTTPStatus, OpenapiResponse]
    default: OpenapiResponse | None = None

    def as_json_dict(self):
        _responses_json = super().as_json_dict(skip_fields={'by_status_code'})
        _responses_json.update(_make_jsonable(self.by_status_code))
        return _responses_json


@dataclasses.dataclass
class OpenapiServer(JsonDataclass):
    url: str
    description: str | None = None
    # variables: Iterable[OpenapiServerVariable]


@dataclasses.dataclass
class OpenapiContact(JsonDataclass):
    name: str | None = None
    url: str | None = None
    email: str | None = None


@dataclasses.dataclass
class OpenapiOperation(JsonDataclass):
    operationId: str
    responses: OpenapiResponses
    summary: str | None = None
    description: str | None = None
    tags: Iterable[str] | None = None
    parameters: Iterable[OpenapiParameter] | None = None
    deprecated: bool = False
    # externalDocs: Optional[OpenapiExternalDocs] = None
    # requestBody: Optional[OpenapiRequestBody] = None
    # callbacks: Optional[Dict[str, OpenapiCallback]] = None
    # security: Optional[Iterable[OpenapiSecurityRequirement]] = None
    # servers: Optional[Iterable[OpenapiServer]] = None


@dataclasses.dataclass
class OpenapiPath(JsonDataclass):
    operations: dict[str, OpenapiOperation]
    summary: str | None = None
    description: str | None = None
    parameters: Iterable[OpenapiParameter] | None = None

    def as_json_dict(self):
        _path_json = super().as_json_dict(skip_fields={'operations'})
        _path_json.update(_make_jsonable(self.operations))
        return _path_json


@dataclasses.dataclass
class OpenapiInfo(JsonDataclass):
    title: str
    version: str
    summary: str | None = None
    description: str | None = None
    termsOfService: str | None = None
    contact: OpenapiContact | None = None
    # license: Optional[OpenapiLicense] = None


@dataclasses.dataclass
class OpenapiRoot(JsonDataclass):
    info: OpenapiInfo
    servers: Iterable[OpenapiServer]
    paths: dict[str, OpenapiPath]
    components: dict
    openapi: str = '3.1.0'
