var commonConfig = require('./karma.common.conf.js');
var assign = require('object-assign');

module.exports = function (config) {
    config.set(assign(commonConfig, {
        browsers: ['PhantomJS'],
        reporters: ['spec'],

        // Avoid DISCONNECTED messages
        // See https://github.com/karma-runner/karma/issues/598
        browserDisconnectTimeout : 10000, // default 2000
        browserDisconnectTolerance : 1, // default 0
        browserNoActivityTimeout : 60000 //default 10000
    }));
};
