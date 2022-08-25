import os
import json

here = os.path.split(os.path.abspath(__file__))[0]

def from_json(fname):
    with open(os.path.join(here, fname)) as f:
        return json.load(f)
