from website.addons.base.logger import AddonNodeLogger

class DmptoolNodeLogger(AddonNodeLogger):

    addon_short_name = 'dmptool'

    def _log_params(self):
        node_settings = self.node.get_addon('dmptool')
        return {
            'project': self.node.parent_id,
            'node': self.node._primary_key,
            'dataset': node_settings.dataset if node_settings else None
        }