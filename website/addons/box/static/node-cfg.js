'use strict';

var AddonNodeConfig = require('js/addonNodeConfig').AddonNodeConfig;
var url = window.contextVars.node.urls.api + 'box/config/';
new AddonNodeConfig('Box', '#boxScope', url, '#boxGrid', {
    onPickFolder: function(evt, item) {
        evt.preventDefault();
        var name = item.data.path === 'All Files' ? '/ (Full Box)' : item.data.path.replace('All Files', '');
        this.selected({
            name: name,
            path: item.data.path,
            id: item.data.id
        });
        return false; // Prevent event propagation
    }
});
