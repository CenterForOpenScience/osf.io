var WEKOUserConfig = require('./wekoUserConfig.js').WEKOUserConfig;

// Endpoint for WEKO settings
var configUrl = '/api/v1/settings/weko/';
var accountsUrl = '/api/v1/settings/weko/accounts/';

var wekoUserConfig = new WEKOUserConfig('#wekoAddonScope', configUrl, accountsUrl);
wekoUserConfig.viewModel.fetch();
