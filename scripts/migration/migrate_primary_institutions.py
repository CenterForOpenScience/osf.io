from modularodm import Q

from website.models import Node, NodeLog
from website.app import init_app


PRIMARY_INSTITUTION_CHANGED = 'primary_institution_changed'
PRIMARY_INSTITUTION_REMOVED = 'primary_institution_removed'

def migrate_logs():
    added_logs = NodeLog.find(Q('action', 'eq', PRIMARY_INSTITUTION_CHANGED))
    for log in added_logs:
        log.action = NodeLog.AFFILIATED_INSTITUTION_ADDED
        log.save()
    removed_logs = NodeLog.find(Q('action', 'eq', PRIMARY_INSTITUTION_REMOVED))
    for log in removed_logs:
        log.action = NodeLog.AFFILIATED_INSTITUTION_REMOVED
        log.save()

def migrate_nodes():
    nodes = Node.find(Q('primary_institution', 'ne', None))
    for node in nodes:
        inst = node.primary_institution
        if inst not in node.affiliated_institutions:
            node.affiliated_institutions.append(inst)
        node.primary_institution = None
        node.save()

def main():
    migrate_logs()
    migrate_nodes()

if __name__ == '__main__':
    init_app()
    main()
