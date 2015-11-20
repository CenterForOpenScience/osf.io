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

// Adding bundle tracker to plugins
common.plugins.concat([
    // for using webpack with Django
    new BundleTracker({filename: './webpack-stats.json'}),
]);

common.output = {
    path: './static/public/js/',
    // publicPath: '/static/', // used to generate urls to e.g. images
    filename: '[name].js',
    sourcePrefix: ''
};

module.exports = assign({}, common, {
    entry: {
        'admin-base-page': staticAdminPath('js/pages/base-page.js')
    },
    debug: true,
    devtool: 'source-map'
});