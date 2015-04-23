import blinker

signals = blinker.Namespace()
contributor_added = signals.signal('contributor-added')
unreg_contributor_added = signals.signal('unreg-contributor-added')
write_permissions_revoked = signals.signal('write-permissions-revoked')

before_register_node = signals.signal('pre-node-register')
after_create_registration = signals.signal('post-create-registration')
after_register_node = signals.signal('post-node-register')
