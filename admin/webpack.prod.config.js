var webpack = require('webpack');
var admin = require('./webpack.admin.config.js');
var assign = require('object-assign');
var SaveAssetsJson = require('assets-webpack-plugin');

module.exports = assign(admin, {
    debug: false,
    devtool: false,
    stats: {reasons: false},
    plugins: admin.plugins.concat([
        new webpack.optimize.DedupePlugin(),
        new webpack.optimize.OccurenceOrderPlugin(),
        new webpack.optimize.AggressiveMergingPlugin(),
        new webpack.DefinePlugin({
            'process.env': {
                NODE_ENV: JSON.stringify('production')
            },
            DEBUG: false,
            '__DEV__': false
        }),
        new webpack.optimize.UglifyJsPlugin({
            exclude: /conference.*?\.js$/,
            compress: {warnings: false}
        }),
        // Save a webpack-assets.json file that maps base filename to filename with
        // hash. This file is used by the webpack_asset mako filter to expand
        // base filenames to full filename with hash.
        new SaveAssetsJson(),
        // Append hash to commons chunk for cachebusting
        new webpack.optimize.CommonsChunkPlugin('vendor', 'vendor.[hash].js'),
    ]),
    output: {
        path: './static/public/js/',
        // publicPath: '/static/', // used to generate urls to e.g. images

        // Append hash to filenames for cachebusting
        filename: '[name].[chunkhash].js',
        sourcePrefix: ''
    }
});
