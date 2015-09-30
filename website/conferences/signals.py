# -*- coding: utf-8 -*-

import blinker

signals = blinker.Namespace()

osf4m_new_user = signals.signal('osf4m-new-user')
