import itertools
from collections import OrderedDict

from django.apps import apps


def sort_dependencies(app_list):
    """Sort a list of (app_label, models) pairs into a single list of models.

    The single list of models is sorted so that any model with a natural key
    is serialized before a normal model, and any model with a natural key
    dependency has it's dependencies serialized first.
    """
    # Process the list of models, and get the list of dependencies
    model_dependencies = []
    models = set()
    for app_label, model_list in app_list.iteritems():
        if model_list is None:
            model_list = apps.get_app_config(app_label).models

        for model in model_list:
            models.add(model)
            # Add any explicitly defined dependencies
            if hasattr(model, 'natural_key'):
                deps = getattr(model.natural_key, 'dependencies', [])
                if deps:
                    deps = [apps.get_model(app_label, dep) for dep in deps]
            else:
                deps = []

            # Now add a dependency for any FK relation with a model that
            # defines a natural key
            for field in model._meta.fields:
                if hasattr(field.rel, 'to'):
                    rel_model = field.rel.to
                    if hasattr(rel_model, 'natural_key') and rel_model != model:
                        deps.append(rel_model)
            # Also add a dependency for any simple M2M relation with a model
            # that defines a natural key.  M2M relations with explicit through
            # models don't count as dependencies.
            for field in model._meta.many_to_many:
                if field.rel.through._meta.auto_created:
                    rel_model = field.rel.to
                    if hasattr(rel_model, 'natural_key') and rel_model != model:
                        deps.append(rel_model)

            model_dependencies.append((model, deps))

    model_dependencies.reverse()
    # Now sort the models to ensure that dependencies are met. This
    # is done by repeatedly iterating over the input list of models.
    # If all the dependencies of a given model are in the final list,
    # that model is promoted to the end of the final list. This process
    # continues until the input list is empty, or we do a full iteration
    # over the input models without promoting a model to the final list.
    # If we do a full iteration without a promotion, that means there are
    # circular dependencies in the list.
    model_list = []
    while model_dependencies:
        skipped = []
        changed = False
        while model_dependencies:
            model, deps = model_dependencies.pop()

            # If all of the models in the dependency list are either already
            # on the final model list, or not on the original serialization list,
            # then we've found another model with all it's dependencies satisfied.
            found = True
            for candidate in ((d not in models or d in model_list) for d in deps):
                if not candidate:
                    found = False
            if found:
                model_list.append(model)
                changed = True
            else:
                skipped.append((model, deps))
        if not changed:
            raise Exception("Can't resolve dependencies for %s in serialized app list." %
                ', '.join('%s.%s' % (model._meta.app_label, model._meta.object_name)
                for model, deps in sorted(skipped, key=lambda obj: obj[0].__name__))
            )
        model_dependencies = skipped

    return model_list


def get_ordered_models():
    all_models = apps.all_models

    model_mapping = OrderedDict()

    for app_label, model_tuples in all_models.iteritems():
        # short circuit, we only get osf apps for now
        if not ('osf' in app_label or 'addons' in app_label):
            continue
        for model_name, model_class in model_tuples.iteritems():
            if app_label not in model_mapping.keys():
                model_mapping[app_label] = []
            model_mapping[app_label].append(model_class)

    ordered_list_of_models = sort_dependencies(model_mapping)
    allowed_models = list(itertools.chain(*[application.get_models(include_auto_created=False) for application in apps.get_app_configs() if 'addons' in application.label or 'osf' in application.label]))

    return [model for model in ordered_list_of_models if model in allowed_models]
