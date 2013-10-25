"""
Create a GUID for all non-GUID database records. If record already has a GUID,
skip; if record has an ID but not a GUID, create a GUID matching the ID. Newly
created records will have optimistically generated GUIDs.
"""

import logging

from website import models
from website.app import init_app

app = init_app("website.settings", set_backends=True, routes=True)

def check_conflicts(models):

    ids = []

    for model in models:
        ids += list(model.find().__iter__(raw=True))

    if len(set(ids)) != len(ids):
        logging.error('Conflict among models {}'.format(
            ', '.join([model._name for model in models])
        ))


optimistic_models = [models.Node, models.User]
objectid_models = [models.NodeLog, models.NodeFile, models.NodeWikiPage,
                   models.Tag, models.MetaData]

logging.debug('Deleting GUID objects...')
for guid_obj in models.Guid.find():
    try:
        guid_obj.remove_one(guid_obj)
    except:
        pass

for model in optimistic_models + objectid_models:
    logging.debug('Migrating model {}...'.format(model._name))
    for obj in model.find():
        guid_obj = models.Guid.load(obj._id)
        if guid_obj is None:
            guid_obj = models.Guid(
                _id=obj._id,
                referent=obj
            )
            try:
                guid_obj.save()
            except:
                print obj._id, obj._name
