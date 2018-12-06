import blinker

signals = blinker.Namespace()

member_added = signals.signal('member-added')
unreg_member_added = signals.signal('unreg-member-added')
