var webpack = require('webpack');
var common = require('./webpack.common.config.js');
var assign = require('object-assign');


// Adding LoaderOptionsPlugin to plugins
var plugins = common.plugins.concat([
    new webpack.LoaderOptionsPlugin({
        debug: true,
    })
]);

var config = assign(common, {
    plugins: plugins
});

module.exports = config;
