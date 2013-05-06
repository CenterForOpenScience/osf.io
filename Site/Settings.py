import os

settings = {}
domain = 'localhost:8080'
framework = 'flask'
debug = False
clearOnLoad = False
emailOnRegister = False
registrationDisabled = False
cacheDirectory = "./Site/Cache"
siteDown = False
database = 'osf20120530' # Mongo
cookieDomain = '.openscienceframework.org' # Beaker
static = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
local = True