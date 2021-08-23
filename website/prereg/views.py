"""Back-end code to support the OSF Preregistration campaign

Keeping the code together in this file should make it easier to remove the
features added to the OSF specifically to support this initiative in the future.

Other resources that are a part of the OSF Preregistration:

* website/static/js/pages/reg-landing-page.js
"""
from website.registries import views

def prereg_landing_page(**kwargs):
    """Landing page for osf prereg"""
    return views._view_registries_landing_page('prereg', **kwargs)
