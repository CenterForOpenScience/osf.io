# TODO: Use django signals
import blinker

signals = blinker.Namespace()
file_updated = signals.signal('file_updated')
