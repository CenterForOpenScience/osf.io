"""Miscellaneous MongoDB utilities

"""

# MongoDB forbids field names that begin with "$" or contain ".". These
# utilities map to and from Mongo field names.

mongo_map= {
    '.': '__!dot!__',
    '$': '__!dollar!__',
}

def to_mongo(item):
    for key, value in mongo_map.items():
        item = item.replace(key, value)
    return item

def from_mongo(item):
    for key, value in mongo_map.items():
        item = item.replace(value, key)
    return item
