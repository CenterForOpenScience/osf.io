from model import UserSettings, NodeSettings, S3File
from .. import Addon

fullname = 'Amazon Simple Storage Service'
shortname = 's3'
provider = 'http://aws.amazon.com/s3/'

addon = Addon(
    fullname=fullname,
    shortname=shortname,
    provider=provider,
    user_model=UserSettings,
    node_model=NodeSettings,
)
addon.register()