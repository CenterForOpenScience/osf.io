import blinker

oauth_signals = blinker.Namespace()
oauth_complete = oauth_signals.signal('oauth-complete')
