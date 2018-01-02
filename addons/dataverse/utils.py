from addons.base.logger import AddonNodeLogger

class DataverseNodeLogger(AddonNodeLogger):

    addon_short_name = 'dataverse'

    def _log_params(self):
        node_settings = self.node.get_addon('dataverse')
        return {
            'project': self.node.parent_id,
            'node': self.node._primary_key,
            'dataset': node_settings.dataset if node_settings else None
        }

def serialize_dataverse_widget(node):
    node_addon = node.get_addon('dataverse')
    widget_url = node.api_url_for('dataverse_get_widget_contents')

    dataverse_widget_data = {
        'complete': node_addon.complete,
        'widget_url': widget_url,
    }
    dataverse_widget_data.update(node_addon.config.to_json())

    return dataverse_widget_data
