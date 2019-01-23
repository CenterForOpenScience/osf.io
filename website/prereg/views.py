"""Back-end code to support the Prereg Challenge initiative

Keeping the code together in this file should make it easier to remove the
features added to the OSF specifically to support this initiative in the future.

Other resources that are a part of the Prereg Challenge:

* website/static/js/pages/reg-landing-page.js
* website/static/css/prereg.css
"""

import waffle

from website.registries import views
from osf import features

def prereg_landing_page(**kwargs):
    """Landing page for osf prereg"""
    if waffle.switch_is_active(features.OSF_PREREGISTRATION):
        return views._view_registries_landing_page('prereg', **kwargs)
    return views._view_registries_landing_page('prereg_challenge', **kwargs)
