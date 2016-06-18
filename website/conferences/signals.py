# -*- coding: utf-8 -*-

import blinker

signals = blinker.Namespace()

osf4m_user_created = signals.signal('osf4m-user-created')
