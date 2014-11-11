var path = require('path');
var fs = require('fs');
var webpack = require('webpack');

var addons = require('./addons.json');
var root = path.join(__dirname, 'website', 'static');
/** Return the absolute path given a path relative to ./website/static */
var fromRoot = function(dir) {
    return path.join(root, dir);
};

/**
 * Return the paths to all addons' modules withe the name `name`.
 *
 * Example:
 *      getAddonModules('index.js')
 *      //=> ['website/addons/dropbox/static/index.js',
 *      //    'website/addons/s3/static/index.js',...]
 * */
var getAddonModules = function(name) {
    var addonModules = [];
    addons.addons.forEach(function(addonName) {
        var addonPath = path.join(__dirname, 'website', 'addons', addonName, 'static', name);
        if (fs.existsSync(addonPath)) {
            addonModules = addonModules.concat([addonPath]);
        }
    });
    return addonModules;
};

module.exports = {
    // Split code chunks by page
    entry: {
        'dashboard': fromRoot('js/pages/dashboard-page.js'),
        'profile': fromRoot('js/pages/profile-page.js'),
        'project-dashboard': fromRoot('js/pages/project-dashboard-page.js'),
        'project-base': fromRoot('js/pages/project-base-page.js'),
        'wiki-edit-page': fromRoot('js/pages/wiki-edit-page.js'),
        // TODO: Optimize common chunks between these modules
        'files-page': fromRoot('js/pages/files-page.js'),
        'addon-index-bundle': getAddonModules('index.js'),
        'addon-files-bundle': getAddonModules('files.js'),
        'addon-node-cfg-bundle': getAddonModules('node-cfg.js')
    },
    debug: true,
    output: {
        path: './website/static/public/js/',
        // publicPath: '/static/', // used to generate urls to e.g. images
        filename: '[name].js'
    },
    resolve: {
        root: root,
        // Look for required files in bower and npm directories
        modulesDirectories: ['./website/static/vendor/bower_components', 'node_modules'],
        // Need to alias libraries that aren't managed by bower or npm
        alias: {
            'knockout-punches': fromRoot('vendor/knockout-punches/knockout.punches.js'),
            'knockout-sortable': fromRoot('vendor/knockout-sortable/knockout-sortable.js'),
            'knockout-validation': fromRoot('vendor/knockout-validation/knockout.validation.min.js'),
            'knockout-mapping': fromRoot('vendor/knockout-mapping/knockout.mapping.js'),
            'bootstrap-editable': fromRoot('vendor/bootstrap3-editable/js/bootstrap-editable.js'),
            'zeroclipboard': fromRoot('vendor/bower_components/zeroclipboard/dist/ZeroClipboard.js'),
            // Needed for knockout-sortable
            'jquery.ui.sortable': fromRoot('vendor/bower_components/jquery-ui/ui/jquery.ui.sortable.js'),
            // Dropzone doesn't have a proper 'main' entry in its bower.json
            'dropzone': fromRoot('vendor/bower_components/dropzone/downloads/dropzone.js'),
            // Also alias some internal libraries for easy access
            'dropzone-patch': fromRoot('js/dropzone-patch.js'),
            'rubeus': fromRoot('js/rubeus.js'),
            'folderpicker': fromRoot('js/folderPicker.js'),
            'osf-helpers': fromRoot('js/osf-helpers.js'),
            'osf-language': fromRoot('js/osf-language.js'),
            'addons': path.join(__dirname, 'website', 'addons')
        }
    },
    plugins: [
        // Bundle common code between modules
        new webpack.optimize.CommonsChunkPlugin('common.js'),
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
        })
    ],
    externals: {
        // require("jquery") is external and available
        //  on the global var jQuery, which is loaded with CDN
        'jquery': 'jQuery',
        'jquery-ui': 'jQuery.ui'
    }
};
