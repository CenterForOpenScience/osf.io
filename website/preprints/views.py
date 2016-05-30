# -*- coding: utf-8 -*-
from framework.flask import redirect  # VOL-aware redirect

def preprint_landing_page(**kwargs):
    return {}


def preprint_redirect(**kwargs):
    return redirect('/preprints/')
