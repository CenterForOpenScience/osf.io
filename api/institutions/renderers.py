from rest_framework_csv.renderers import CSVRenderer


class MetricsCSVRenderer(CSVRenderer):
    """
    CSVRenderer with updated render method to export `data` dictionary of API Response to CSV
    """

    def render(self, data, media_type=None, renderer_context=None, writer_opts=None):
        """
        Overwrites CSVRenderer.render() to create a CSV with the data dictionary
        instead of the entire API response. This is necessary for results to be
        separated into different rows.
        """
        if not renderer_context:
            renderer_context = {}
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


class InstitutionDashboardCSVRenderer(CSVRenderer):
    """
    MetricsCSVRenderer with headers and labels specific to the InstitutionDepartmentMetrics Endpoint
    """

    def render(self, data, media_type=None, renderer_context=None, writer_opts=None):
        """
        Overwrite the render() method to dynamically create a CSV with headers based on the serializer fields.
        This is necessary for the results to be accurately represented in rows, and for the CSV to adapt to changes in the serializer.
        """
        if renderer_context is None:
            renderer_context = {}

        # Retrieve the serializer from the context to get the fields
        view = renderer_context.get('view')
        serializer = view.get_serializer() if view else None

        # Dynamically generate headers based on the serializer fields
        fields = serializer.Meta.fields
        self.header = [field if isinstance(field, str) else field.source for field in fields]
        self.labels = {field: field.replace('attributes.', '') for field in self.header}

        data = data.get('data', [])
        return super().render(
            data,
            media_type=media_type,
            renderer_context=renderer_context,
            writer_opts=writer_opts
        )
