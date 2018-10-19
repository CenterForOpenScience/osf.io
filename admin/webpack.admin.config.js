var webpack = require('webpack');
var path = require('path');
var common = require('../webpack.common.config.js');
var BundleTracker = require('webpack-bundle-tracker');

var websiteRoot = path.resolve(__dirname, '..', 'website', 'static');

var adminRoot = path.resolve(__dirname, 'static');

var staticAdminPath = function(dir) {
    return path.resolve(adminRoot, dir);
};

var staticPath = function(dir) {
    return path.join(websiteRoot, dir);
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
        'maintenance': staticAdminPath('js/maintenance/maintenance.js'),
        'rdm-addons-page': staticAdminPath('js/rdm_addons/rdm-addons-page.js'),
        'rdm-dataverse-cfg': staticAdminPath('js/rdm_addons/dataverse/rdm-cfg.js'),
        'rdm-s3-cfg': staticAdminPath('js/rdm_addons/s3/rdm-cfg.js'),
        'rdm-owncloud-cfg': staticAdminPath('js/rdm_addons/owncloud/rdm-cfg.js'),
        'rdm-figshare-cfg': staticAdminPath('js/rdm_addons/figshare/rdm-cfg.js'),
        'rdm-timestampsettings-page': staticAdminPath('js/rdm_timestampsettings/rdm-timestampsettings-page.js'),
        'rdm-keymanagement-page': staticAdminPath('js/rdm_keymanagement/rdm-keymanagement-page.js'),
        'embedded-wayf_disp': staticAdminPath('js/shib-login/embedded-wayf_disp.js'),
        'embedded-wayf_config': staticAdminPath('js/shib-login/embedded-wayf_config.js'),
        'cas': staticAdminPath('js/shib-login/cas.js'),
    },
    plugins: plugins,
    devtool: 'source-map',
});
config.resolve.modules.push(websiteRoot, adminRoot);
module.exports = config;
