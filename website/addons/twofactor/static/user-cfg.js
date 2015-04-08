var TwoFactorUserConfig = require('./twoFactorUserConfig.js').TwoFactorUserConfig;

// Initialize tfa user config widget
new TwoFactorUserConfig('#twoFactorScope', '#twoFactorQrCode');
