import blinker

signals = blinker.Namespace()

archive_fail = signals.signal('archive-fail')
