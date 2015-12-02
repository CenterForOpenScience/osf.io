from modularodm import Q

from website.app import init_app
from website.models import Institution, User
from framework.transactions.context import TokuTransaction


INSTITUTIONS = [
    {
        'name': 'Virginia Tech',
        '_id': 'VT'
    },
    {
        'name': 'Notre Dame',
        '_id': 'ND'
    }
]

def update_or_create(inst):
    new_inst = Institution.load(inst['_id'])
    if new_inst:
        for key, val in inst.iteritems():
            new_inst.key = val
        new_inst.save()
        return new_inst, False
    new_inst = Institution(**inst)
    new_inst.save()
    return new_inst, True

def add_institutions():
    user = User.find_one(Q('username', 'eq', 'qwe@net.com'))
    for inst in INSTITUTIONS:
        with TokuTransaction():
            new_inst, inst_created = update_or_create(inst)
            if inst_created:
                user.affiliated_institutions.append(new_inst)
                user.save()

def main():
    init_app()
    add_institutions()

if __name__ == '__main__':
    main()
