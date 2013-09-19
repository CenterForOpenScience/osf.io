from model import UserSettings, NodeSettings, DataverseFile
from .. import Addon

fullname = 'DataVerse'
shortname = 'dataverse'
provider = 'http://thedata.org/'

addon = Addon(
    fullname=fullname,
    shortname=shortname,
    provider=provider,
    user_model=UserSettings,
    node_model=NodeSettings,
)
addon.register()