# TODO: Use django signals
import blinker

signals = blinker.Namespace()
file_updated = signals.signal('file_updated')
file_viewed = signals.signal('file_viewed')
file_downloaded = signals.signal('file_downloaded')
