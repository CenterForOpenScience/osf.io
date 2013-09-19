from model import DataverseUserSettings, DataverseNodeSettings, DataverseFile
from .. import Addon

fullname = 'Dataverse'
shortname = 'dataverse'
provider = 'http://thedata.org/'

addon = Addon(
    fullname=fullname,
    shortname=shortname,
    provider=provider,
    user_model=DataverseUserSettings,
    node_model=DataverseNodeSettings,
)
addon.register()