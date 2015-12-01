# This should be the browser for dryad

from website.addons.dryad import api

import httplib
import logging
import datetime
import browser

from flask import request
from framework.flask import redirect

from framework.exceptions import HTTPError
from website.project.decorators import must_have_permission
from website.project.decorators import must_not_be_registration
from website.project.decorators import must_have_addon, must_be_valid_project
from website.project.views.node import _view_project

from website.addons.dryad.api import Dryad_DataOne

logger = logging.getLogger(__name__)

import xml.etree.ElementTree as ET


@must_be_valid_project
@must_have_addon('dryad', 'node')
def dryad_add_to_project(**kwargs):
	return 0