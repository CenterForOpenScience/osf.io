var commonConfig = require('./karma.common.conf.js');
var assign = require('object-assign');

module.exports = function (config) {
    config.set(assign(commonConfig, {
        browsers: ['PhantomJS'],
        reporters: ['spec'],
    }));
};
