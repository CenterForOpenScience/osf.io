var TwoFactorUserConfig = require('./twoFactorUserConfig.js');

var otpURL = window.contextVars.otpauthURL;
// Initialize tfa user config widget
new TwoFactorUserConfig('#twoFactorScope', '#twoFactorQrCode', otpURL);
