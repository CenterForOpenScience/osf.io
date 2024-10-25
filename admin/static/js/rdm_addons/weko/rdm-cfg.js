const $ = require('jquery');
const $osf = require('js/osfHelpers');
const WEKOUserConfig = require('./wekoRdmConfig.js').WEKOUserConfig;

const institutionId = $('#wekoAddonScope').data('institution-id');
const url = '/addons/api/v1/settings/weko/' + institutionId + '/accounts/';
const userConfig = new WEKOUserConfig('#wekoAddonScope', url, institutionId);
userConfig.start();