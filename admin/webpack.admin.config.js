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
        'admin-registration-edit-page': staticAdminPath('js/pages/admin-registration-edit-page.js'),
        'dashboard': staticAdminPath('js/sales_analytics/dashboard.js'),
        'metrics-page': staticAdminPath('js/pages/metrics-page.js'),
        'banners': staticAdminPath('js/banners/banners.js'),
        'brands': staticAdminPath('js/brands/brands.js'),
        'maintenance': staticAdminPath('js/maintenance/maintenance.js'),
        'whitelist-page': staticAdminPath('js/pages/whitelist-page.js'),
        'collection-provider-page': staticAdminPath('js/pages/collection-provider-page.js'),
        'registration-provider-page': staticAdminPath('js/pages/registration-provider-page.js'),
        'rdm-addons-page': staticAdminPath('js/rdm_addons/rdm-addons-page.js'),
        'rdm-dataverse-cfg': staticAdminPath('js/rdm_addons/dataverse/rdm-cfg.js'),
        'rdm-s3-cfg': staticAdminPath('js/rdm_addons/s3/rdm-cfg.js'),
        'rdm-owncloud-cfg': staticAdminPath('js/rdm_addons/owncloud/rdm-cfg.js'),
        'rdm-figshare-cfg': staticAdminPath('js/rdm_addons/figshare/rdm-cfg.js'),
        'rdm-iqbrims-cfg': staticAdminPath('js/rdm_addons/iqbrims/rdm-cfg.js'),
        'rdm-weko-cfg': staticAdminPath('js/rdm_addons/weko/rdm-cfg.js'),
        'rdm-timestampsettings-page': staticAdminPath('js/rdm_timestampsettings/rdm-timestampsettings-page.js'),
        'rdm-timestampadd-page': staticAdminPath('js/rdm_timestampadd/rdm-timestampadd-page.js'),
        'rdm-keymanagement-page': staticAdminPath('js/rdm_keymanagement/rdm-keymanagement-page.js'),
        'rdm-institutional-storage-page': staticAdminPath('js/rdm_custom_storage_location/rdm-institutional-storage-page.js'),
        'rdm-metadata-page': staticAdminPath('js/rdm_metadata/rdm-metadata-page.js'),
    },
    plugins: plugins,
    devtool: 'source-map',
});
config.resolve.modules.push(websiteRoot, adminRoot);
module.exports = config;
