'use strict';

var AddonNodeConfig = require('js/addonNodeConfig').AddonNodeConfig;

var url = window.contextVars.node.urls.api + 'googledrive/config/';
new AddonNodeConfig('Google Drive', '#googledriveScope', url, '#googledriveGrid',
    {
        decodeFolder: (function(folder_name) {
            return decodeURIComponent(folder_name);
        })
    }
);

