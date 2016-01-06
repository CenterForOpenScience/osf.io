from modularodm import Q

def get_prereg_schema():
    from website.models import MetaSchema  # noqa

    return MetaSchema.find_one(
        Q('name', 'eq', 'Prereg Challenge') &
        Q('schema_version', 'eq', 2)
    )
