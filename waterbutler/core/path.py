import os
import itertools
from waterbutler.core import exceptions


class WaterButlerPathPart:
    DECODE = lambda x: x
    ENCODE = lambda x: x

    def __init__(self, part, _id=None):
        self._id = _id
        self._count = 0
        self._orig_id = _id
        self._orig_part = part
        self._name, self._ext = os.path.splitext(self.original_value)

    @property
    def identifier(self):
        return self._id

    @property
    def value(self):
        if self._count:
            return'{} ({}){}'.format(self._name, self._count, self._ext)
        return'{}{}'.format(self._name, self._ext)

    @property
    def raw(self):
        return self.__class__.ENCODE(self.value)

    @property
    def original_value(self):
        return self.__class__.DECODE(self._orig_part)

    @property
    def original_raw(self):
        return self._orig_part

    @property
    def ext(self):
        return self._ext

    def increment_name(self, _id=None):
        self._id = _id
        self._count += 1
        return self

    def renamed(self, name):
        return self.__class__(self.__class__.ENCODE(name), _id=self._id)

    def __repr__(self):
        return '{}({!r}, count={})'.format(self.__class__.__name__, self._orig_part, self._count)


class WaterButlerPath:
    """
    A standardized and validated immutable WaterButler path.
    """

    PART_CLASS = WaterButlerPathPart

    @classmethod
    def generic_path_validation(cls, path):
        """Validates a WaterButler specific path, e.g. /folder/file.txt, /folder/
        :param str path: WaterButler path
        """
        if not path:
            raise exceptions.InvalidPathError('Must specify path')
        if not path.startswith('/'):
            raise exceptions.InvalidPathError('Invalid path \'{}\' specified'.format(path))
        if '//' in path:
            raise exceptions.InvalidPathError('Invalid path \'{}\' specified'.format(path))
        # Do not allow path manipulation via shortcuts, e.g. '..'
        absolute_path = os.path.abspath(path)
        if not path == '/' and path.endswith('/'):
            absolute_path += '/'
        if not path == absolute_path:
            raise exceptions.InvalidPathError('Invalid path \'{}\' specified'.format(absolute_path))

    @classmethod
    def validate_folder(cls, path):
        if not path.is_dir:
            raise exceptions.CreateFolderError('Path must be a directory', code=400)

        if path.is_root:
            raise exceptions.CreateFolderError('Path can not be root', code=400)

    @classmethod
    def from_parts(cls, parts, folder=False, **kwargs):
        _ids, _parts = [], []
        for part in parts:
            _ids.append(part.identifier)
            _parts.append(part.raw)

        path = '/'.join(_parts)
        if parts and not path:
            path = '/'

        return cls(path, _ids=_ids, folder=folder, **kwargs)

    def __init__(self, path, _ids=(), prepend=None, folder=None):
        self.__class__.generic_path_validation(path)

        self._orig_path = path

        self._prepend = prepend

        if prepend:
            self._prepend_parts = [self.PART_CLASS(part, None) for part in prepend.rstrip('/').split('/')]
        else:
            self._prepend_parts = []

        self._parts = [
            self.PART_CLASS(part, _id)
            for _id, part in
            itertools.zip_longest(_ids, path.rstrip('/').split('/'))
        ]

        if folder is not None:
            self._is_folder = bool(folder)
        else:
            self._is_folder = self._orig_path.endswith('/')

        if self.is_dir and not self._orig_path.endswith('/'):
            self._orig_path += '/'

    @property
    def is_root(self):
        return len(self._parts) == 1

    @property
    def is_dir(self):
        return self._is_folder

    @property
    def is_file(self):
        return not self._is_folder

    @property
    def parts(self):
        return self._parts

    @property
    def name(self):
        return self._parts[-1].value

    @property
    def identifier(self):
        return self._parts[-1].identifier

    @property
    def ext(self):
        return self._parts[-1].ext

    @property
    def path(self):
        if len(self.parts) == 1:
            return ''
        return '/'.join([x.value for x in self.parts[1:]]) + ('/' if self.is_dir else '')

    @property
    def raw_path(self):
        if len(self.parts) == 1:
            return ''
        return '/'.join([x.raw for x in self.parts[1:]]) + ('/' if self.is_dir else '')

    @property
    def full_path(self):
        return '/'.join([x.value for x in self._prepend_parts + self.parts[1:]]) + ('/' if self.is_dir else '')

    @property
    def parent(self):
        if len(self.parts) == 1:
            return None
        return self.__class__.from_parts(self.parts[:-1], folder=True, prepend=self._prepend)

    def child(self, name, _id=None, folder=False):
        return self.__class__.from_parts(self.parts + [self.PART_CLASS(name, _id=_id)], folder=folder, prepend=self._prepend)

    def increment_name(self):
        self._parts[-1].increment_name()
        return self

    def rename(self, name):
        self._parts[-1] = self._parts[-1].renamed(name)
        return self

    def __eq__(self, other):
        return isinstance(other, self.__class__) and str(self) == str(other)

    def __str__(self):
        return '/'.join([x.value for x in self.parts]) + ('/' if self.is_dir else '')

    def __repr__(self):
        return '{}({!r}, prepend={!r})'.format(self.__class__.__name__, self._orig_path, self._prepend)
