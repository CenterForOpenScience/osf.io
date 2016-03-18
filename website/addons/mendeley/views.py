# -*- coding: utf-8 -*-
from .provider import MendeleyCitationsProvider
from website.citations.views import GenericCitationViews

mendeley_views = GenericCitationViews('mendeley', MendeleyCitationsProvider)
