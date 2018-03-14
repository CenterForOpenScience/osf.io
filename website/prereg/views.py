"""Back-end code to support the Prereg Challenge initiative

Keeping the code together in this file should make it easier to remove the
features added to the OSF specifically to support this initiative in the future.

Other resources that are a part of the Prereg Challenge:

* website/static/js/pages/prereg-landing-page.js
* website/static/css/prereg.css
"""

from website.registries import views

def prereg_landing_page(**kwargs):
    """Landing page for the prereg challenge"""
    return views._view_registries_landing_page('prereg', **kwargs)
