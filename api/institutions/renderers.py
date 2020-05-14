from rest_framework_csv.renderers import CSVRenderer


class MetricsCSVRenderer(CSVRenderer):
    header = ['id', 'attributes.user_name', 'attributes.public_projects', 'attributes.private_projects', 'type']
    labels = {
        'attributes.private_projects': 'private_projects',
        'attributes.public_projects': 'public_projects',
        'attributes.user_name': 'user_name',
    }

    def render(self, data, media_type=None, renderer_context={}, writer_opts=None):
        """
        Renders serialized *data* into CSV. For a dictionary:
        """
        data = data.get('data')
        return super().render(data, media_type=media_type, renderer_context=renderer_context, writer_opts=writer_opts)
