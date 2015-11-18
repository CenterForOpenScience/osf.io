import blinker

signals = blinker.Namespace()

guid_stored_object_saved = signals.signal('guid_stored_object_saved')
