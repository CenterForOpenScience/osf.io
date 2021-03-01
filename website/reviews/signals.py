import blinker


signals = blinker.Namespace()
reviews_email = signals.signal('reviews_email')
reviews_email_submit = signals.signal('reviews_email_submit')
reviews_email_submit_moderators_notifications = signals.signal('reviews_email_submit_moderators_notifications')
reviews_withdraw_requests_notification_moderators = signals.signal('reviews_withdraw_requests_notification_moderators')
email_withdrawal_requests = signals.signal('email_withdrawal_requests')
reviews_email_withdrawal_requests = signals.signal('reviews_email_withdrawal_requests')
