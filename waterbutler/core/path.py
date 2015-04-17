import os

class WaterButlerPathPart:
    DECODE = lambda x: x
    ENCODE = lambda x: x

    def __init__(self, part, _id=None):
        self._id = _id
        self._part = part

    @property
    def identifier(self):
        return self._id

    @property
    def value(self):
        return self.__class__.DECODE(self._part)

    @property
    def raw(self):
        return self._part

    def __repr__(self):
        return '{}({!r})'.format(self.__class__.__name__, self._part)


class WaterButlerPath:
    """
    A standardized and validated immutable WaterButler path.
    """

    PART_CLASS = WaterButlerPathPart

    @classmethod
    def from_parts(cls, parts, folder=False):
        _ids, _parts = [], ['']
        for part in parts:
            _ids.append(part.identifier)
            _parts.append(part.raw)

        return cls('/'.join(_parts), _ids=_ids, folder=folder)

    def __init__(self, path, _ids=(), prepend=None, folder=None):
        self._generic_path_validation(path)

        self._orig_path = path
        path = path.strip('/').split('/')

        _ids = [None] * len(_ids) - len(path) + _ids

        self._parts = [
            self.PART_CLASS(part, _id)
            for part, _id
            in zip(path, _ids)
        ]

        if folder is not None:
            self.is_folder = bool(folder)
        else:
            self.is_folder = self.path.endswith('/')

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
    def path(self):
        return '/'.join([x.value for x in self.parts])

    @property
    def parent(self):
        return self.__class__.from_parts(self.parts[:-1])

    def _generic_path_validation(self, path):
        pass

    def __str__(self):
        return '/'.join([''] + [x.raw for x in self.parts]) + ('/' if self.is_folder else '')

    def __repr__(self):
        return '{}({!r})'.format(self.__class__.__name__, self._orig_path)
