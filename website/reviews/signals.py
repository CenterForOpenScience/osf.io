import blinker


signals = blinker.Namespace()
reviews_email = signals.signal('reviews_email')
reviews_email_submit = signals.signal('reviews_email_submit')
reviews_email_submit_moderators_notifications = signals.signal('reviews_email_submit_moderators_notifications')
