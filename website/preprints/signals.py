import blinker

signals = blinker.Namespace()
preprint_submitted = signals.signal('preprint-submitted')
