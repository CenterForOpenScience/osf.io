# -*- coding: utf-8 -*-
import os

import mfr
import mfr_audio
import mfr_code_pygments
import mfr_docx
import mfr_image
import mfr_ipynb
import mfr_movie
import mfr_pdb
import mfr_pdf
import mfr_rst
import mfr_tabular

HANDLERS = [
    mfr_audio.Handler,
    mfr_image.Handler,
    mfr_movie.Handler,
    mfr_pdb.Handler,
    mfr_pdf.Handler,
    mfr_rst.Handler,
    mfr_tabular.Handler,
    mfr_ipynb.Handler,
    mfr_docx.Handler,
    mfr_code_pygments.Handler,
]


def init_mfr(app):
    """Register all available FileHandlers and collect each
    plugin's static assets to the app's static path.
    """
    # Available file handlers
    mfr.register_filehandlers(HANDLERS)

    # Update mfr config with static path and url
    mfr.config.update({
        # Base URL for static files
        'ASSETS_URL': os.path.join(app.static_url_path, 'mfr'),
        # Where to save static files
        'ASSETS_FOLDER': os.path.join(app.static_folder, 'mfr'),
    })
    mfr.collect_static(dest=mfr.config['ASSETS_FOLDER'])
