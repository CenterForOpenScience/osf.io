import blinker

signals = blinker.Namespace()

member_added = signals.signal('member-added')
unreg_member_added = signals.signal('unreg-member-added')
group_added_to_node = signals.signal('group-added')
