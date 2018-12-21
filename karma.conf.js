var commonConfig = require('./karma.common.conf.js');
var assign = require('object-assign');

module.exports = function (config) {
    config.set(assign(commonConfig, {
        browsers: ['ChromeHeadless', 'ChromeHeadlessNoSandbox'],
        reporters: ['spec'],
        // https://github.com/travis-ci/docs-travis-ci-com/pull/1671/files
        customLaunchers: {
            ChromeHeadlessNoSandbox: {
                base: 'ChromeHeadless',
                flags: ['--no-sandbox']
            }
        },
    }));
};
