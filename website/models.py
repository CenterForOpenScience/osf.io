# -*- coding: utf-8 -*-
import logging
from framework import db, storage
from framework.auth.model import User
from framework.search.model import Keyword
from framework.sessions.model import Session

from website.project.model import (ApiKey, Node, NodeLog, NodeFile, NodeWikiPage,
                                   Tag, WatchConfig)
from framework.mongo import set_up_storage


MODELS = (User, ApiKey, Keyword, ApiKey, Node, NodeLog, NodeFile, NodeWikiPage,
          Tag, WatchConfig, Session)
