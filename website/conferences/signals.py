# -*- coding: utf-8 -*-

import blinker

signals = blinker.Namespace()

new_osf4m_user = signals.signal('new-osf4m-user')
