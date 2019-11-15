var $ = require('jquery');
var $osf = require('js/osfHelpers');
var IQBRIMSUserConfig = require('./iqbrimsRdmConfig.js').IQBRIMSUserConfig;

var institutionId = $('#iqbrimsAddonScope').data('institution-id');
var url = '/addons/api/v1/settings/iqbrims/' + institutionId + '/accounts/';
var iqbrimsUserConfig = new IQBRIMSUserConfig('#iqbrimsAddonScope', url, institutionId);
