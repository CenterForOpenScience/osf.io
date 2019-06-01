'use strict';

var OauthAddonNodeConfig = require('js/oauthAddonNodeConfig').OauthAddonNodeConfig;

var url = window.contextVars.node.urls.api + 'iqbrims/config/';
new OauthAddonNodeConfig('IQB-RIMS', '#iqbrimsScope', url, '#iqbrimsGrid');

// Test function for register paper
var $osf = require('js/osfHelpers');
window.testIQBRIMSRegisterPaper = function (registerType, laboName) {
    console.log('start testIQBRIMSRegisterPaper()');
    var url = window.contextVars.node.urls.api + 'iqbrims/config/register-paper/';
    return $osf.putJSON(
        url, {
            register_type: registerType,
            labo_name: laboName
        }
    ).done(function (data) {
        console.log('done', {'data': data});
    }).fail(function (xhr, status, error) {
        console.error('fail', {'xhr': xhr, 'status': status, 'error': error});
    });
};
