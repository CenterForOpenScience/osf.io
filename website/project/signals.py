import blinker

signals = blinker.Namespace()
contributor_added = signals.signal('contributor-added')
project_created = signals.signal('project-created')
contributor_removed = signals.signal('contributor-removed')
unreg_contributor_added = signals.signal('unreg-contributor-added')
write_permissions_revoked = signals.signal('write-permissions-revoked')
node_deleted = signals.signal('node-deleted')

after_create_registration = signals.signal('post-create-registration')

archive_callback = signals.signal('archive-callback')
