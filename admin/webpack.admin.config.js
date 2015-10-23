var webpack = require('webpack');
var path = require('path');
var common = require('./webpack.common.config.js');
var assign = require('object-assign');
var BundleTracker = require('webpack-bundle-tracker');

var root = path.join(__dirname, 'website', 'static');

var staticPath = function(dir) {
    return path.join(root, dir);
};

var entry = {
    // JS
    'base-page': staticPath('js/pages/base-page.js'),
    'home-page': staticPath('js/pages/home-page.js'),
    'dashboard-page': staticPath('js/pages/dashboard-page.js'),
    'profile-page': staticPath('js/pages/profile-page.js'),
    'project-dashboard': staticPath('js/pages/project-dashboard-page.js'),
    'project-base-page': staticPath('js/pages/project-base-page.js'),
    'wiki-edit-page': staticPath('js/pages/wiki-edit-page.js'),
    'file-page': staticPath('js/pages/file-page.js'),
    'files-page': staticPath('js/pages/files-page.js'),
    'profile-settings-page': staticPath('js/pages/profile-settings-page.js'),
    'profile-account-settings-page': staticPath('js/pages/profile-account-settings-page.js'),
    'profile-settings-applications-list-page': staticPath('js/pages/profile-settings-applications-list-page.js'),
    'profile-settings-applications-detail-page': staticPath('js/pages/profile-settings-applications-detail-page.js'),
    'register_1-page': staticPath('js/pages/register_1-page.js'),
    'sharing-page': staticPath('js/pages/sharing-page.js'),
    'conference-page': staticPath('js/pages/conference-page.js'),
    'meetings-page': staticPath('js/pages/meetings-page.js'),
    'view-file-tree-page': staticPath('js/pages/view-file-tree-page.js'),
    'project-settings-page': staticPath('js/pages/project-settings-page.js'),
    'search-page': staticPath('js/pages/search-page.js'),
    'registration-retraction-page': staticPath('js/pages/registration-retraction-page.js'),
    'share-search-page': staticPath('js/pages/share-search-page.js'),
    'profile-settings-addons-page': staticPath('js/pages/profile-settings-addons-page.js'),
    'twofactor-page': staticPath('js/pages/twofactor-page.js'),
    'forgotpassword-page': staticPath('js/pages/forgotpassword-page.js'),
    'login-page': staticPath('js/pages/login-page.js'),
    'notifications-config-page': staticPath('js/pages/notifications-config-page.js'),
    'share-embed-page': staticPath('js/pages/share-embed-page.js'),
    'render-nodes': staticPath('js/pages/render-nodes.js'),
    // Commons chunk
    'vendor': [
        // Vendor libraries
        'knockout',
        'knockout.validation',
        'knockout.punches',
        'moment',
        'bootstrap',
        'bootbox',
        'bootstrap-editable',
        'select2',
        'dropzone',
        'knockout-sortable',
        'treebeard',
        'jquery.cookie',
        'URIjs',
        // Common internal modules
        'js/fangorn',
        'js/citations',
        'js/osfHelpers',
        'js/osfToggleHeight',
        'mithril'
    ]
};


// Adding bundle tracker to plugins
var plugins = [
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

module.exports = assign(common, {
    debug: true,
    devtool: 'source-map'
});
