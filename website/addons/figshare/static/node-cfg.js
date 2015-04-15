'use strict';

var AddonNodeConfig = require('js/addonNodeConfig').AddonNodeConfig;

var url = window.contextVars.node.urls.api + 'figshare/config/';
new AddonNodeConfig('figshare', '#figshareScope', url, '#figshareGrid', {
    onPickFolder: function (evt, item) {
        evt.preventDefault();
        this.selected({name: item.data.name, type: item.data.type, id: item.data.id});
        return false; // Prevent event propagation
    }
});
