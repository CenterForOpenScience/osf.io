/**
 *
 */
var fs = require('fs');

var commonConfig = require('./karma.common.conf.js');
var assign = require('object-assign');

var browsers = {
    sl_chrome: {
        base: 'SauceLabs',
        browserName: 'chrome',
        version: '40'
    },
    sl_firefox: {
        base: 'SauceLabs',
        browserName: 'firefox',
    },
    sl_safari: {
        base: 'SauceLabs',
        browserName: 'safari',
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
    }
    // TODO: Sinon faker is not compatible with IE 9. Github issue: https://github.com/cjohansen/Sinon.JS/issues/715
    //sl_ie_9: {
    //    base: 'SauceLabs',
    //    browserName: 'internet explorer',
    //    platform: 'Windows 7',
    //    version: '9'
    //}
};

// Use ENV vars on Travis and sauce.json locally to get credentials
if (!process.env.SAUCE_USERNAME) {
    if (!fs.existsSync('sauce.json')) {
        console.log('Create a sauce.json with your credentials based on the sauce-sample.json file.');
        process.exit(1);
    } else {
        process.env.SAUCE_USERNAME = require('./sauce').username;
        process.env.SAUCE_ACCESS_KEY = require('./sauce').accessKey;
    }
}

module.exports = function(config) {
    config.set(assign(commonConfig, {
        reporters: ['saucelabs', 'spec'],
        browsers: Object.keys(browsers),
        customLaunchers: browsers,
        singleRun: true
    }));
};
