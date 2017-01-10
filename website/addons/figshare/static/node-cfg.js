'use strict';

var OauthAddonNodeConfig = require('js/oauthAddonNodeConfig').OauthAddonNodeConfig;

var url = window.contextVars.node.urls.api + 'figshare/settings/';
new OauthAddonNodeConfig('figshare', '#figshareScope', url, '#figshareGrid', {
    onPickFolder: function (evt, item) {
        evt.preventDefault();
        this.selected({name: item.data.name, type: item.data.type, id: item.data.id});
        return false; // Prevent event propagation
    }
});
