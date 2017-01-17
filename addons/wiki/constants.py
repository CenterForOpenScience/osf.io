from . import routes

ROUTES = [routes.widget_routes, routes.page_routes, routes.api_routes]

SHORT_NAME = 'wiki'
FULL_NAME = 'Wiki'

OWNERS = ['node']

ADDED_DEFAULT = ['node']
ADDED_MANDATORY = []

VIEWS = ['widget', 'page']
CONFIGS = []

CATEGORIES = ['documentation']

INCLUDE_JS = {
    'widget': [],
    'page': [],
}

INCLUDE_CSS = {
    'widget': [],
    'page': [],
}
