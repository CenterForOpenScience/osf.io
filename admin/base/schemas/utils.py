# -*- coding: utf-8 -*-
import json
import os

here = os.path.split(os.path.abspath(__file__))[0]


def from_json(file_name):
    with open(os.path.join(here, file_name)) as f:
        return json.load(f)
