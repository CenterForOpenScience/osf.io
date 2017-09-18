from addons.base.logger import AddonNodeLogger

class WEKONodeLogger(AddonNodeLogger):

    addon_short_name = 'weko'

    def _log_params(self):
        node_settings = self.node.get_addon('weko')
        return {
            'project': self.node.parent_id,
            'node': self.node._primary_key,
            'index': node_settings.index_id if node_settings else None
        }
