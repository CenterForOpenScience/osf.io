import blinker

signals = blinker.Namespace()
contributor_added = signals.signal('contributor-added')
contributor_removed = signals.signal('contributor-removed')
unreg_contributor_added = signals.signal('unreg-contributor-added')
write_permissions_revoked = signals.signal('write-permissions-revoked')

after_create_registration = signals.signal('post-create-registration')

archive_callback = signals.signal('archive-callback')

privacy_set_public = signals.signal('privacy_set_public')
