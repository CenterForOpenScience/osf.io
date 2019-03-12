# -*- coding: utf-8 -*-

def used_quota(user_id):
    return 1000

def abbreviate_size(size):
    size = float(size)
    abbr_dict = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}

    power = 0
    while size > 1024 and power < 4:
        size /= 1024
        power += 1

    return (size, abbr_dict[power])
