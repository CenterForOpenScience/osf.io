from framework.flask import redirect  # VOL-aware redirect


def preprint_redirect(**kwargs):
    return redirect('/preprints/')
