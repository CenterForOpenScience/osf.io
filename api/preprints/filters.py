from api.base.filters import ListFilterMixin


class PreprintsListFilterMixin(ListFilterMixin):

    def should_filter_special_param(self, field_name):
        """ This should be overridden in subclasses for custom filtering behavior
        """
        return field_name == 'provider'

    def filter_special_param(self, params, filter_list):
        """ This should be overridden in subclasses for custom filtering behavior
        """
        return [
            preprint for preprint in filter_list
            if preprint.provider._id == params['value']
        ]
