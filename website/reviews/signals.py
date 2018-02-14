import blinker


signals = blinker.Namespace()
reviews_email = signals.signal('reviews_email')
reviews_email_submit = signals.signal('reviews_email_submit')
