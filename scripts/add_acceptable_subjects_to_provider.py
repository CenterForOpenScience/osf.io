from modularodm import Q

from website.app import init_app
from website.models import Subject, PreprintProvider

def find_child_and_grandchild(grandpa, childIndex=0):
    parent = Subject.find(Q('parents', 'eq', grandpa))[childIndex]
    try:
        child = Subject.find(Q('parents', 'eq', parent))[0]
    except IndexError:
        return find_child_and_grandchild(grandpa, childIndex=childIndex+1)
    return parent, child

def create_subject_rules():
    top_levels = Subject.find(Q('parents', 'eq', []))
    subA = top_levels[0]
    subB = top_levels[1]
    subC = top_levels[2]

    children_of_A = Subject.find(Q('parents', 'eq', subA))
    subD = children_of_A[0]
    subE = children_of_A[1]

    subF, subG = find_child_and_grandchild(subB)

    rules = [
        ([subA._id, subD._id], False),
        ([subA._id, subE._id], True),
        ([subB._id, subF._id, subG._id], True),
        ([subC._id], True)
    ]
    return rules

def main():
    provider = PreprintProvider.find()[0]
    provider.subjects_acceptable = create_subject_rules()
    provider.save()

if __name__ == '__main__':
    init_app(set_backends=True)
    main()
