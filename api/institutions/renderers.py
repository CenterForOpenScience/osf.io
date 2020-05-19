from rest_framework_csv.renderers import CSVRenderer


class MetricsCSVRenderer(CSVRenderer):
    """
    CSVRenderer with updated render method to export `data` dictionary of API Response to CSV
    """

    def render(self, data, media_type=None, renderer_context={}, writer_opts=None):
        """
        Overwrites CSVRenderer.render() to create a CSV with the data dictionary
        instead of the entire API response. This is necessary for results to be
        separated into different rows.
        """
        data = data.get('data')
        return super().render(data, media_type=media_type, renderer_context=renderer_context, writer_opts=writer_opts)

class InstitutionUserMetricsCSVRenderer(MetricsCSVRenderer):
    """
    MetricsCSVRenderer with headers and labels specific to the InstitutionUserMetrics Endpoint
    """

    header = ['id', 'attributes.user_name', 'attributes.public_projects', 'attributes.private_projects', 'type']
    labels = {
        'attributes.private_projects': 'private_projects',
        'attributes.public_projects': 'public_projects',
        'attributes.user_name': 'user_name',
    }

class InstitutionDepartmentMetricsCSVRenderer(MetricsCSVRenderer):
    """
    MetricsCSVRenderer with headers and labels specific to the InstitutionDepartmentMetrics Endpoint
    """

    header = ['id', 'attributes.name', 'attributes.number_of_users', 'type']
    labels = {
        'attributes.name': 'name',
        'attributes.number_of_users': 'number_of_users',
    }
