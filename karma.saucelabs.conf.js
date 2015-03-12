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
  sl_ie_11: {
    base: 'SauceLabs',
    browserName: 'internet explorer',
    platform: 'Windows 8.1',
    version: '11'
  }
};

module.exports = function(config) {
  config.set(assign(commonConfig, {
      reporters: ['saucelabs', 'spec'],
      browsers: Object.keys(browsers),
      customLaunchers: browsers,
      singleRun: true,

      // Avoid DISCONNECTED messages
      // See https://github.com/karma-runner/karma/issues/598
      browserDisconnectTimeout : 100000, // default 2000
      browserNoActivityTimeout : 600000 //default 10000
  }));
};