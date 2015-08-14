from rest_framework.exceptions import ValidationError


class IncludeParametersMixin(object):

    def check_includes(self, include_parameters, data):
        invalid_parameters = []
        for parameter in include_parameters:
            if parameter not in data.keys():
                invalid_parameters.append(parameter)
        raise ValidationError('{}'.format(invalid_parameters))
