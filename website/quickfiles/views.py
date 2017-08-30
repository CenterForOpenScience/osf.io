# -*- coding: utf-8 -*-
import os
from flask import send_from_directory
from website.settings import EXTERNAL_EMBER_APPS

quickfiles_dir = os.path.abspath(os.path.join(os.getcwd(), EXTERNAL_EMBER_APPS['quickfiles']['path']))

def quickfiles_landing_page(**kwargs):
    return {}

def use_ember_app(**kwargs):
    return send_from_directory(quickfiles_dir, 'index.html')