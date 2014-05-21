# -*- coding: utf-8 -*-

import blinker


signals = blinker.Namespace()

load = signals.signal('load')

before_save = signals.signal('before_save')
save = signals.signal('save')
