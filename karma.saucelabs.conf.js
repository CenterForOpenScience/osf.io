/**
 *
 */

var commonConfig = require('./karma.common.conf.js');
var assign = require('object-assign');

var browsers = {
  sl_chrome: {
    base: 'SauceLabs',
    browserName: 'chrome',
    platform: 'Windows 7',
    version: '35'
  },
  sl_firefox: {
    base: 'SauceLabs',
    browserName: 'firefox',
    version: '30'
  },
  sl_safari: {
    base: 'SauceLabs',
    browserName: 'safari',
    version: '8'
  },
  sl_ie_11: {
    base: 'SauceLabs',
    browserName: 'internet explorer',
    platform: 'Windows 8.1',
    version: '11'
  },
  sl_ie_10: {
    base: 'SauceLabs',
    browserName: 'internet explorer',
    platform: 'Windows 8',
    version: '10'
  },
  sl_ie_9: {
    base: 'SauceLabs',
    browserName: 'internet explorer',
    platform: 'Windows 7',
    version: '9'
  }
};

module.exports = function(config) {
  config.set(assign(commonConfig, {
      reporters: ['saucelabs', 'spec'],
      browsers: Object.keys(browsers),
      customLaunchers: browsers,
      singleRun: true,
  }));
};