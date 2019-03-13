# -*- coding: utf-8 -*-

def used_quota(user_id):
    return 1000

def get_ratio_to_quota_temp(usage, max_limit):
    print(usage)
    print(max_limit)
    print((usage/max_limit)*100)
    return float(usage)/float(max_limit) * float(100)

def get_max_limit_temp(user_id):
    return float(100000)
