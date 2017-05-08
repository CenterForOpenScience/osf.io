var SwiftUserConfig = require('./swiftUserConfig.js').SwiftUserConfig;

// Endpoint for Swift user settings
var url = '/api/v1/settings/swift/accounts/';

var swiftUserConfig = new SwiftUserConfig('#swiftAddonScope', url);
