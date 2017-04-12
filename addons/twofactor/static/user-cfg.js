var TwoFactorUserConfig = require('./twoFactorUserConfig.js').TwoFactorUserConfig;

// Initialize tfa user config widget
var SETTINGS_URL = '/api/v1/settings/twofactor/';
new TwoFactorUserConfig(SETTINGS_URL, '#twoFactorScope', '#twoFactorQrCode');
