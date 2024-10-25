import json
import os

here = os.path.split(os.path.abspath(__file__))[0]

def from_json(fname):
    with open(os.path.join(here, fname)) as f:
        return json.load(f)

REGISTRATION_METADATA_MAPPINGS = [
    ('公的資金による研究データのメタデータ登録', from_json('e-rad-metadata-mappings.json')),
]
