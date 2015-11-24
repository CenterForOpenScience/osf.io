var webpack = require('webpack');
var path = require('path');
var common = require('../webpack.common.config.js');
var assign = require('object-assign');
var BundleTracker = require('webpack-bundle-tracker');

var websiteRoot = path.join(__dirname, 'websiteRoot', 'static');

var adminRoot = path.join(__dirname, 'static');

var staticWebsitePath = function(dir) {
    return path.join(websiteRoot, dir);
};

var staticAdminPath = function(dir) {
    return path.join(adminRoot, dir);
};

common.entry['admin-base-page'] = staticAdminPath('js/pages/base-page.js');

// Adding bundle tracker to plugins
common.plugins = [
    // Bundle common code between modules
    new webpack.optimize.CommonsChunkPlugin('vendor', 'vendor.js'),
    // Bower support
    new webpack.ResolverPlugin(
        new webpack.ResolverPlugin.DirectoryDescriptionFilePlugin('bower.json', ['main'])
    ),
    // Make jQuery available in all modules without having to do require('jquery')
    new webpack.ProvidePlugin({
        $: 'jquery',
        jQuery: 'jquery'
    }),
    // Slight hack to make sure that CommonJS is always used
    new webpack.DefinePlugin({
        'define.amd': false
    }),
    // for using webpack with Django
    new BundleTracker({filename: './webpack-stats.json'}),
];

common.output = {
    path: './static/public/js/',
    // publicPath: '/static/', // used to generate urls to e.g. images
    filename: '[name].js',
    sourcePrefix: ''
};

module.exports = assign(common, {
    debug: true,
    devtool: 'source-map'
});