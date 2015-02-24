# -*- coding: utf-8 -*-

import blinker

signals = blinker.Namespace()
user_registered = signals.signal('user-registered')
user_confirmed = signals.signal('user-confirmed')
contributor_removed = signals.signal('contributor-removed')
node_deleted = signals.signal('node-deleted')