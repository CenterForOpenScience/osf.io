from rest_framework.exceptions import ValidationError

class IncludeParametersMixin(object):

    def process_includes(self, include_parameters, data, serializer):
        invalid_parameters = []
        for parameter in include_parameters:
            contained = False
            for element in data:
                if contained:
                    break
                if parameter in element:
                    contained = True
            if not contained:
                invalid_parameters.append(parameter)

        if invalid_parameters:
            raise ValidationError('{} are invalid parameters.'.format(invalid_parameters))
        return data