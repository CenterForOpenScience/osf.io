var webpack = require('webpack');
var path = require('path');
var common = require('../webpack.common.config.js');
var BundleTracker = require('webpack-bundle-tracker');

var websiteRoot = path.resolve(__dirname, '..', 'website', 'static');

var adminRoot = path.resolve(__dirname, 'static');

var staticAdminPath = function(dir) {
    return path.resolve(adminRoot, dir);
};

// Adding bundle tracker to plugins
var plugins = common.plugins.concat([
    // for using webpack with Django
    new BundleTracker({filename: './webpack-stats.json'}),
    new webpack.LoaderOptionsPlugin({
        debug: true,
        minimize: true
    })
]);

common.output = {
    path: path.resolve(__dirname, 'static', 'public', 'js'),
    // publicPath: '/static/', // used to generate urls to e.g. images
    filename: '[name].js',
    sourcePrefix: ''
};

var config = Object.assign({}, common, {
    entry: {
        'admin-base-page': staticAdminPath('js/pages/base-page.js'),
        'prereg-admin-page': staticAdminPath('js/pages/prereg-admin-page.js'),
        'admin-registration-edit-page': staticAdminPath('js/pages/admin-registration-edit-page.js'),
        'dashboard': staticAdminPath('js/sales_analytics/dashboard.js'),
        'metrics-page': staticAdminPath('js/pages/metrics-page.js'),
        'banners': staticAdminPath('js/banners/banners.js'),
        'maintenance': staticAdminPath('js/maintenance/maintenance.js'),
    },
    plugins: plugins,
    devtool: 'source-map',
});
config.resolve.modules.push(websiteRoot, adminRoot);
module.exports = config;
