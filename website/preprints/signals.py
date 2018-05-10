import blinker

signals = blinker.Namespace()

contributor_added = signals.signal('contributor-added')
project_created = signals.signal('preprint-created')
contributor_removed = signals.signal('contributor-removed')
unreg_contributor_added = signals.signal('unreg-contributor-added')
write_permissions_revoked = signals.signal('write-permissions-revoked')
privacy_set_public = signals.signal('privacy_set_public')
