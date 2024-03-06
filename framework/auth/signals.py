# -*- coding: utf-8 -*-

import blinker

signals = blinker.Namespace()
user_registered = signals.signal('user-registered')
user_confirmed = signals.signal('user-confirmed')
user_email_removed = signals.signal('user-email-removed')
user_merged = signals.signal('user-merged')
user_account_deactivated = signals.signal('user-account-deactivated')
user_account_reactivated = signals.signal('user-account-reactivated')

unconfirmed_user_created = signals.signal('unconfirmed-user-created')
