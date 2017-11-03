var webpack = require('webpack');
var common = require('./webpack.common.config.js');
var assign = require('object-assign');

module.exports = assign(common, {
    plugins: [
        new webpack.LoaderOptionsPlugin({
            debug: true
        })
    ]
});
