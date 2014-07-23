# -*- coding: utf-8 -*-


def get_extension(filename):
    parts = filename.split('.')
    if len(parts) > 1:
        return '.' + parts[-1]
    return parts[-1]
