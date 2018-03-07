var webpack = require('webpack');
var path = require('path');
var fs = require('fs');

var SaveAssetsJson = require('assets-webpack-plugin');

var addons = require('./addons.json');
var root = path.resolve(__dirname, 'website', 'static');
/** Return the absolute path given a path relative to ./website/static */
var staticPath = function(dir) {
    return path.resolve(root, dir);
};
var nodePath = function(dir) {
    return path.resolve(__dirname, 'node_modules', dir);
};
var addonsPath = function(dir) {
    return path.resolve(__dirname, 'addons', dir);
};

/**
 * Each JS module for a page on the OSF is webpack entry point. These are built
 * to website/static/public/
 */
var entry = {
    // JS
    'base-page': staticPath('js/pages/base-page.js'),
    'home-page': staticPath('js/pages/home-page.js'),
    'landing-page': staticPath('js/pages/landing-page.js'),
    'dashboard-page': staticPath('js/pages/dashboard-page.js'),
    'profile-page': staticPath('js/pages/profile-page.js'),
    'project-dashboard': staticPath('js/pages/project-dashboard-page.js'),
    'project-base-page': staticPath('js/pages/project-base-page.js'),
    'project-settings-page': staticPath('js/pages/project-settings-page.js'),
    'project-addons-page': staticPath('js/pages/project-addons-page.js'),
    'project-registrations-page': staticPath('js/pages/project-registrations-page.js'),
    'registration-retraction-page': staticPath('js/pages/registration-retraction-page.js'),
    'registration-edit-page': staticPath('js/pages/registration-edit-page.js'),
    'register-page': staticPath('js/pages/register-page.js'),
    'wiki-edit-page': staticPath('js/pages/wiki-edit-page.js'),
    'statistics-page': staticPath('js/pages/statistics-page.js'),
    'file-page': staticPath('js/pages/file-page.js'),
    'files-page': staticPath('js/pages/files-page.js'),
    'prereg-landing-page': staticPath('js/pages/prereg-landing-page.js'),
    'profile-settings-page': staticPath('js/pages/profile-settings-page.js'),
    'profile-account-settings-page': staticPath('js/pages/profile-account-settings-page.js'),
    'profile-settings-applications-list-page': staticPath('js/pages/profile-settings-applications-list-page.js'),
    'profile-settings-applications-detail-page': staticPath('js/pages/profile-settings-applications-detail-page.js'),
    'profile-settings-personal-tokens-list-page': staticPath('js/pages/profile-settings-personal-tokens-list-page.js'),
    'profile-settings-personal-tokens-detail-page': staticPath('js/pages/profile-settings-personal-tokens-detail-page.js'),
    'sharing-page': staticPath('js/pages/sharing-page.js'),
    'conference-page': staticPath('js/pages/conference-page.js'),
    'meetings-page': staticPath('js/pages/meetings-page.js'),
    'view-file-tree-page': staticPath('js/pages/view-file-tree-page.js'),
    'search-page': staticPath('js/pages/search-page.js'),
    'profile-settings-addons-page': staticPath('js/pages/profile-settings-addons-page.js'),
    'forgotpassword-page': staticPath('js/pages/forgotpassword-page.js'),
    'resetpassword-page': staticPath('js/pages/resetpassword-page.js'),
    'claimaccount-page': staticPath('js/pages/claimaccount-page.js'),
    'login-page': staticPath('js/pages/login-page.js'),
    'notifications-config-page': staticPath('js/pages/notifications-config-page.js'),
    'render-nodes': staticPath('js/pages/render-nodes.js'),
    'institution-page': staticPath('js/pages/institution-page.js'),
    // Commons chunk
    'vendor': [
        // Vendor libraries
        'knockout',
        'knockout.validation',
        'moment',
        'bootstrap',
        'bootbox',
        'bootstrap-editable',
        'select2',
        'dropzone',
        'knockout-sortable',
        'loaders.css',
        'treebeard',
        'lodash.get',
        'js-cookie',
        'URIjs',
        // Common internal modules
        'js/fangorn',
        'js/citations',
        'js/osfHelpers',
        'js/osfToggleHeight',
        'mithril',
        // Main CSS files that get loaded above the fold
        nodePath('select2/select2.css'),
        nodePath('bootstrap/dist/css/bootstrap.css'),
        '@centerforopenscience/osf-style',
        staticPath('css/style.css'),
    ],
};

// Collect log text from addons
var mainLogs = require(staticPath('js/logActionsList.json'));
var anonymousLogs = require(staticPath('js/anonymousLogActionsList.json'));
var addonLog;
var anonymousAddonLog;

// Collect addons endpoints. If an addon's static folder has
// any of the following files, it will be added as an entry point
// and output to website/static/public/js/<addon-name>/files.js
var addonModules = ['files.js', 'node-cfg.js', 'user-cfg.js', 'file-detail.js', 'widget-cfg.js'];
addons.addons.forEach(function(addonName) {
    var baseDir = addonName + '/';
    addonModules.forEach(function(module) {
        var modulePath = path.resolve(__dirname, 'addons',
                                  addonName, 'static', module);
        if (fs.existsSync(modulePath)) {
            var entryPoint = baseDir + module.split('.')[0];
            entry[entryPoint] =  modulePath;
        }
    });
    var logTextPath = path.resolve(__dirname, 'addons',
        addonName, 'static', addonName + 'LogActionList.json');
    if(fs.existsSync(logTextPath)){
        addonLog = require(logTextPath);
        for (var attrname in addonLog) { mainLogs[attrname] = addonLog[attrname]; }
    }
    var anonymousLogTextPath = path.resolve(__dirname, 'addons',
        addonName, 'static', addonName + 'AnonymousLogActionList.json');
    if(fs.existsSync(anonymousLogTextPath)) {
        anonymousAddonLog = require(anonymousLogTextPath);
        for (var log in anonymousAddonLog) { anonymousLogs[log] = anonymousAddonLog[log]; }
    }
});

fs.writeFileSync(staticPath('js/_allLogTexts.json'), JSON.stringify(mainLogs));
fs.writeFileSync(staticPath('js/_anonymousLogTexts.json'), JSON.stringify(anonymousLogs));

var resolve = {
    modules: [
        root,
        './website/static/vendor/bower_components',
        'node_modules',
    ],
    extensions: ['*', '.es6.js', '.js', '.min.js'],
    // Need to alias libraries that aren't managed by bower or npm
    alias: {
        'knockout-sortable': staticPath('vendor/knockout-sortable/knockout-sortable.js'),
        'bootstrap-editable': staticPath('vendor/bootstrap-editable-custom/js/bootstrap-editable.js'),
        'jquery-blockui': staticPath('vendor/jquery-blockui/jquery.blockui.js'),
        'bootstrap': nodePath('bootstrap/dist/js/bootstrap.js'),
        'Caret.js': staticPath('vendor/bower_components/Caret.js/dist/jquery.caret.min.js'),
        'osf-panel': staticPath('vendor/bower_components/osf-panel/dist/jquery-osfPanel.min.js'),
        'jquery-qrcode': staticPath('vendor/bower_components/jquery-qrcode/jquery.qrcode.min.js'),
        'jquery-tagsinput': staticPath('vendor/bower_components/jquery.tagsinput/jquery.tagsinput.js'),
        'clipboard': staticPath('vendor/bower_components/clipboard/dist/clipboard.js'),
        'history': nodePath('historyjs/scripts/bundled/html4+html5/jquery.history.js'),
        // Needed for knockout-sortable
        'jquery.ui.sortable': staticPath('vendor/bower_components/jquery-ui/ui/widgets/sortable.js'),
        'truncate': staticPath('vendor/bower_components/truncate/jquery.truncate.js'),
        // Needed for ace code editor in wiki
        'ace-noconflict': staticPath('vendor/bower_components/ace-builds/src-noconflict/ace.js'),
        'ace-ext-language_tools': staticPath('vendor/bower_components/ace-builds/src-noconflict/ext-language_tools.js'),
        'ace-mode-markdown': staticPath('vendor/bower_components/ace-builds/src-noconflict/mode-markdown.js'),
        'pagedown-ace-converter': addonsPath('wiki/static/pagedown-ace/Markdown.Converter.js'),
        'pagedown-ace-sanitizer': addonsPath('wiki/static/pagedown-ace/Markdown.Sanitizer.js'),
        'pagedown-ace-editor': addonsPath('wiki/static/pagedown-ace/Markdown.Editor.js'),
        'wikiPage': addonsPath('wiki/static/wikiPage.js'),
        'typo': staticPath('vendor/ace-plugins/typo.js'),
        'highlight-css': nodePath('highlight.js/styles/default.css'),
        'pikaday-css': nodePath('pikaday/css/pikaday.css'),
        // Also alias some internal libraries for easy access
        'addons': path.resolve(__dirname, 'addons'),
        'tests': staticPath('js/tests'),
        // GASP Items not defined as main in its package.json
        'TweenLite' : nodePath('gsap/src/minified/TweenLite.min.js'),
        'EasePack' : nodePath('gsap/src/minified/easing/EasePack.min.js'),
        'keen-dataset' : nodePath('keen-dataviz/lib/dataset/'),
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
    new webpack.optimize.CommonsChunkPlugin({ name: 'vendor', filename: 'vendor.js' }),
    // Make jQuery available in all modules without having to do require('jquery')
    new webpack.ProvidePlugin({
        $: 'jquery',
        jQuery: 'jquery'
    }),
    // Slight hack to make sure that CommonJS is always used
    new webpack.DefinePlugin({
        'define.amd': false,
        '__ENABLE_DEV_MODE_CONTROLS': fs.existsSync(staticPath(path.join('built', 'git_logs.json')))
    }),
];

var output = {
    path: path.resolve(__dirname, 'website', 'static', 'public', 'js'),
    // publicPath: '/static/', // used to generate urls to e.g. images
    filename: '[name].js',
    sourcePrefix: ''
};

module.exports = {
    entry: entry,
    resolve: resolve,
    devtool: 'source-map',
    externals: externals,
    plugins: plugins,
    output: output,
    module: {
        rules: [
            {test: /\.es6\.js$/, exclude: [/node_modules/, /bower_components/, /vendor/], loader: 'babel-loader'},
            {test: /\.css$/, use: [{loader: 'style-loader'}, {loader: 'css-loader'}]},
            // url-loader uses DataUrls; files-loader emits files
            {test: /\.png$/, loader: 'url-loader?limit=100000&mimetype=image/ng'},
            {test: /\.gif$/, loader: 'url-loader?limit=10000&mimetype=image/gif'},
            {test: /\.jpg$/, loader: 'url-loader?limit=10000&mimetype=image/jpg'},
            {test: /\.woff(2)?(\?v=[0-9]\.[0-9]\.[0-9])?$/, loader: 'url-loader?mimetype=application/font-woff'},
            {test: /\.svg/, loader: 'file-loader'},
            {test: /\.eot/, loader: 'file-loader'},
            {test: /\.ttf/, loader: 'file-loader'},
            { parser: { amd: false }}
        ]
    },
    node: {
       fs: 'empty'
    }
};
