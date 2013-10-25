# -*- coding: utf-8 -*-
'''Consolidates all necessary models from the framework and website packages.
'''
from framework.auth.model import User
from framework.sessions.model import Session

from website.project.model import (ApiKey, Node, NodeLog, NodeFile, NodeWikiPage,
                                   Tag, WatchConfig)

# All models
MODELS = (User, ApiKey, ApiKey, Node, NodeLog, NodeFile, NodeWikiPage,
          Tag, WatchConfig, Session)
