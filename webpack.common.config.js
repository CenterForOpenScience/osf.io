var webpack = require('webpack');
var path = require('path');
var fs = require('fs');

var SaveAssetsJson = require('assets-webpack-plugin');

var addons = require('./addons.json');
var root = path.join(__dirname, 'website', 'static');
/** Return the absolute path given a path relative to ./website/static */
var staticPath = function(dir) {
    return path.join(root, dir);
};
var nodePath = function(dir) {
    return path.join(__dirname, 'node_modules', dir);
};
var addonsPath = function(dir) {
    return path.join(__dirname, 'website', 'addons', dir);
};

/**
 * Each JS module for a page on the OSF is webpack entry point. These are built
 * to website/static/public/
 */
var entry = {
    // JS
    'base-page': staticPath('js/pages/base-page.js'),
    'home-page': staticPath('js/pages/home-page.js'),
    'dashboard-page': staticPath('js/pages/dashboard-page.js'),
    'profile-page': staticPath('js/pages/profile-page.js'),
    'project-dashboard': staticPath('js/pages/project-dashboard-page.js'),
    'project-base-page': staticPath('js/pages/project-base-page.js'),
    'wiki-edit-page': staticPath('js/pages/wiki-edit-page.js'),
    'files-page': staticPath('js/pages/files-page.js'),
    'profile-settings-page': staticPath('js/pages/profile-settings-page.js'),
    'register_1-page': staticPath('js/pages/register_1-page.js'),
    'sharing-page': staticPath('js/pages/sharing-page.js'),
    'conference-page': staticPath('js/pages/conference-page.js'),
    'view-file-page': staticPath('js/pages/view-file-page.js'),
    'new-folder-page': staticPath('js/pages/new-folder-page.js'),
    'project-settings-page': staticPath('js/pages/project-settings-page.js'),
    'search-page': staticPath('js/pages/search-page.js'),
    'share-search-page': staticPath('js/pages/share-search-page.js'),
    'user-addon-cfg-page': staticPath('js/pages/user-addon-cfg-page.js'),
    'notifications-config-page': staticPath('js/notifications-config-page.js'),
    // Commons chunk
    'vendor': [
        // Vendor libraries
        'knockout',
        'knockout-validation',
        'bootstrap',
        'bootbox',
        'select2',
        'knockout-punches',
        'dropzone',
        'knockout-sortable',
        'treebeard',
        'jquery.cookie',
        'URIjs',
        // Common internal modules
        'fangorn',
        'citations',
        'osfHelpers'
    ]
};

// Collect adddons endpoints. If an addon's static folder has
// any of the following files, it will be added as an entry point
// and output to website/static/public/js/<addon-name>/files.js
var addonModules = ['files.js', 'node-cfg.js', 'user-cfg.js', 'file-detail.js', 'widget-cfg.js'];
addons.addons.forEach(function(addonName) {
    var baseDir = addonName + '/';
    addonModules.forEach(function(module) {
        var modulePath = path.join(__dirname, 'website', 'addons',
                                  addonName, 'static', module);
        if (fs.existsSync(modulePath)) {
            var entryPoint = baseDir + module.split('.')[0];
            entry[entryPoint] =  modulePath;
        }
    });
});

var resolve = {
    root: root,
    // Look for required files in bower and npm directories
    modulesDirectories: ['./website/static/vendor/bower_components', 'node_modules'],
    // Need to alias libraries that aren't managed by bower or npm
    alias: {
        'knockout-punches': staticPath('vendor/knockout-punches/knockout.punches.js'),
        'knockout-sortable': staticPath('vendor/knockout-sortable/knockout-sortable.js'),
        'knockout-validation': staticPath('vendor/knockout-validation/knockout.validation.js'),
        'knockout-mapping': staticPath('vendor/knockout-mapping/knockout.mapping.js'),
        'bootstrap-editable': staticPath('vendor/bower_components/x-editable/dist/bootstrap3-editable/js/bootstrap-editable.js'),
        'jquery-blockui': staticPath('vendor/jquery-blockui/jquery.blockui.js'),
        'zeroclipboard': staticPath('vendor/bower_components/zeroclipboard/dist/ZeroClipboard.js'),
        'bootstrap': staticPath('vendor/bower_components/bootstrap/dist/js/bootstrap.min.js'),
        'jquery-tagsinput': staticPath('vendor/bower_components/jquery.tagsinput/jquery.tagsinput.js'),
        'jquery.cookie': staticPath('vendor/bower_components/jquery.cookie/jquery.cookie.js'),
        'history': staticPath('vendor/bower_components/history.js/scripts/bundled/html4+html5/jquery.history.js'),
        // Needed for knockout-sortable
        'jquery.ui.sortable': staticPath('vendor/bower_components/jquery-ui/ui/jquery.ui.sortable.js'),
        // Dropzone doesn't have a proper 'main' entry in its bower.json
        'dropzone': staticPath('vendor/bower_components/dropzone/dist/dropzone.js'),
        'truncate': staticPath('vendor/bower_components/truncate/jquery.truncate.js'),
        // Needed for ace code editor in wiki
        'ace-noconflict': staticPath('vendor/bower_components/ace-builds/src-noconflict/ace.js'),
        'ace-ext-language_tools': staticPath('vendor/bower_components/ace-builds/src-noconflict/ext-language_tools.js'),
        'ace-mode-markdown': staticPath('vendor/bower_components/ace-builds/src-noconflict/mode-markdown.js'),
        'pagedown-ace-converter': addonsPath('wiki/static/pagedown-ace/Markdown.Converter.js'),
        'pagedown-ace-sanitizer': addonsPath('wiki/static/pagedown-ace/Markdown.Sanitizer.js'),
        'pagedown-ace-editor': addonsPath('wiki/static/pagedown-ace/Markdown.Editor.js'),
        'wikiPage': addonsPath('wiki/static/wikiPage.js'),
        'c3': staticPath('vendor/bower_components/c3/c3.js'),
        'highlight-css': nodePath('highlight.js/styles/default.css'),
        // Also alias some internal libraries for easy access
        'fangorn': staticPath('js/fangorn.js'),
        'waterbutler': staticPath('js/waterbutler.js'),
        'folderpicker': staticPath('js/folderPicker.js'),
        'osfHelpers': staticPath('js/osfHelpers.js'),
        'osfLanguage': staticPath('js/osfLanguage.js'),
        'addons': path.join(__dirname, 'website', 'addons'),
        'addonHelper': staticPath('js/addonHelper.js'),
        'koHelpers': staticPath('js/koHelpers.js'),
        'addonPermissions': staticPath('js/addonPermissions.js'),
        'navbar-control': staticPath('js/navbarControl.js'),
        'markdown': staticPath('js/markdown.js'),
        "diffTool": staticPath('js/diffTool.js'),
        'mathrender': staticPath('js/mathrender.js'),
        'citations': staticPath('js/citations.js')
    }
};

var externals = {
    // require("jquery") is external and available
    //  on the global var jQuery, which is loaded with CDN
    'jquery': 'jQuery',
    'jquery-ui': 'jQuery.ui',
    'raven-js': 'Raven',
    'MathJax': 'MathJax'
};

var plugins = [
    // Bundle common code between modules
    new webpack.optimize.CommonsChunkPlugin('vendor', 'vendor.[hash].js'),
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
    new SaveAssetsJson()
];


var output = {
    path: './website/static/public/js/',
    // publicPath: '/static/', // used to generate urls to e.g. images
    filename: '[name].[chunkhash].js',
    sourcePrefix: ''
};

module.exports = {
    entry: entry,
    resolve: resolve,
    externals: externals,
    plugins: plugins,
    output: output,
    module: {
        loaders: [
            {test: /\.css$/, loaders: ['style', 'css']},
            // url-loader uses DataUrls; files-loader emits files
            {test: /\.png$/, loader: 'url-loader?limit=100000&mimetype=image/png'},
            {test: /\.gif$/, loader: 'url-loader?limit=10000&mimetype=image/gif'},
            {test: /\.jpg$/, loader: 'url-loader?limit=10000&mimetype=image/jpg'},
            {test: /\.woff/, loader: 'url-loader?limit=10000&mimetype=application/font-woff'},
            {test: /\.svg/, loader: 'file-loader'},
            {test: /\.eot/, loader: 'file-loader'},
            {test: /\.ttf/, loader: 'file-loader'}
        ]
    }
};
