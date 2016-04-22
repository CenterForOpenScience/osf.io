from modularodm.exceptions import ValidationValueError


def copy_files(src, target_node, parent=None, name=None):
    """Copy the files from src to the target node
    :param Folder src: The source to copy children from
    :param Node target_node: The node settings of the project to copy files to
    :param Folder parent: The parent of to attach the clone of src to, if applicable
    """
    assert not parent or not parent.is_file, 'Parent must be a folder'

    cloned = src.clone().wrapped()
    cloned.parent = parent
    cloned.node = target_node
    cloned.name = name or cloned.name
    cloned.copied_from = src

    if src.is_file:
        cloned.versions = src.versions

    cloned.save()

    if not src.is_file:
        for child in src.children:
            copy_files(child, target_node, parent=cloned)

    return cloned


class GenWrapper(object):
    """A Wrapper for MongoQuerySets
    Overrides __iter__ so for loops will always
    return wrapped objects.
    All other methods are proxied to the underlying QuerySet
    """
    def __init__(self, mqs):
        self.mqs = mqs

    def __iter__(self):
        """Returns a generator that wraps all StoredFileNodes
        returned from self.mqs
        """
        return (x.wrapped() for x in self.mqs)

    def __repr__(self):
        return '<website.files.utils.GenWrapper({!r})>'.format(self.mqs)

    def __getitem__(self, x):
        """__getitem__ does not default to __getattr__
        so it must be explicitly overriden
        """
        return self.mqs[x].wrapped()

    def __len__(self):
        """__len__ does not default to __getattr__
        so it must be explicitly overriden
        """
        return len(self.mqs)

    def __getattr__(self, name):
        if 'mqs' in self.__dict__:
            try:
                return getattr(self.mqs, name)
            except AttributeError:
                pass  # Avoids error message about the underlying object
        return object.__getattribute__(self, name)

    def limit(self, *args, **kwargs):
        return self.__class__(self.mqs.limit(*args, **kwargs))

def validate_location(value):
    if value is None:
        return  # Allow for None locations but not broken dicts
    from website.addons.osfstorage import settings
    for key in ('service', settings.WATERBUTLER_RESOURCE, 'object'):
        if key not in value:
            raise ValidationValueError('Location {} missing key "{}"'.format(value, key))


def insort(col, element, get=lambda x: x):
    """Python's bisect does not allow for a get/key
    so it can not be used on a list of dictionaries.
    Inserts element into the sorted collection col via
    a binary search.
    if element is not directly compairable the kwarg get may
    be a callable that transforms element into a compairable object.
    ie: A lambda that returns a certain key of a dict or attribute of an object
    :param list col: The collection to insort into
    :param ? element: The Element to be insortted into col
    :param callable get: A callable that take a type of element and returns a compairable
    """
    if not col:
        # If collection is empty go ahead and insert at the first position
        col.insert(0, element)
        return col

    lo, hi = 0, len(col)

    # Binary search for the correct position
    while lo < hi:
        mid = int((hi + lo) / 2)
        if get(col[mid]) > get(element):
            hi = mid
        else:
            lo = mid + 1

    col.insert(lo, element)

    return col
