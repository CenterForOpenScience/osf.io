# -*- coding: utf-8 -*-
import logging
from jinja2 import Template

from . import SHORT_NAME


logger = logging.getLogger(__name__)


def append_user_social(ret, user):
    addon = user.get_addon(SHORT_NAME)
    if addon is None:
        return
    ret['eRadResearcherNumber'] = addon.get_erad_researcher_number()

def unserialize_user_social(json_data, user):
    erad_researcher_number = json_data.get('eRadResearcherNumber', None)
    addon = user.get_addon(SHORT_NAME)
    if not addon:
        user.add_addon(SHORT_NAME)
        addon = user.get_addon(SHORT_NAME)
    addon.set_erad_researcher_number(erad_researcher_number)

def make_report_as_csv(format, draft_metadata):
    template = Template(format.csv_template)
    template_metadata = draft_metadata
    return 'report.csv', template.render(**template_metadata)
