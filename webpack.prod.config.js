var webpack = require('webpack');
var common = require('./webpack.common.config.js');

module.exports = {
    // Split code chunks by page
    entry: common.entry,
    resolve: common.resolve,
    externals: common.externals,
    output: common.output,
    debug: true,
    plugins: common.plugins.concat([
        new webpack.optimize.DedupePlugin(),
        new webpack.optimize.OccurenceOrderPlugin(),
        new webpack.optimize.AggressiveMergingPlugin(),
        new webpack.optimize.UglifyJsPlugin({exclude: /conference.*?\.js$/})
    ])
};
