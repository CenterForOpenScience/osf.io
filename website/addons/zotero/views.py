# -*- coding: utf-8 -*-
from .provider import ZoteroCitationsProvider
from website.citations.views import GenericCitationViews

zotero_views = GenericCitationViews('zotero', ZoteroCitationsProvider)
