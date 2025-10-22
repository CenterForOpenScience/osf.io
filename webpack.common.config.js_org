var webpack = require('webpack');
var gettextParser = require('gettext-parser');
var path = require('path');
var fs = require('fs');

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
 * Each JS module for a page on the GakuNin RDM is webpack entry point. These are built
 * to website/static/public/
 */
var entry = {
    // JS
    'wiki-edit-page': staticPath('js/pages/wiki-edit-page.js'),
    // Commons chunk
    'vendor': [
        // Vendor libraries
        'knockout',
        'knockout.validation',
        'moment',
        'bootstrap',
        'bootbox',
        'bootstrap-editable',
        'bootstrap-datepicker',
        'select2',
        'dropzone',
        //'knockout-sortable',
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

function logEntriesToJS(logs) {
    var lines = '';
    var phase = 0;
    Object.entries(logs).forEach(function(entry) {
        if (entry[0] === '##comment##') {
            lines += `//${entry[1]}\n`;
            return;
        }
        if (phase === 0) {
            lines += 'var _ = require(\'js/rdmGettext\')._;\n';
            phase ++;
        }
        lines += `var ${entry[0]} = _('${entry[1].replace(/'/g, '\\\'')}');\n`;
    });
    return lines;
}

function rdmPoToJson() {
    var acceptLanguages = ['en','ja'];
    var translationsBaseDir = 'translations';
    var getTextDomain = 'js_messages';
    var poRelativePath = path.resolve(__dirname, 'website', translationsBaseDir) + '/';
    var jsonRelativePath = path.resolve(__dirname, 'website', 'static', 'js', translationsBaseDir) + '/';
    var localeDir = 'LC_MESSAGES';
    var langCode;
    var input;
    var po;
    for(var i=0 ; i<acceptLanguages.length ; i++){
        langCode = acceptLanguages[i];
        input = fs.readFileSync(poRelativePath + langCode + '/' + localeDir + '/' + getTextDomain + '.po');
        po = gettextParser.po.parse(input);
        fs.writeFileSync(jsonRelativePath + langCode + '.json' , JSON.stringify(po));
    }
}

rdmPoToJson();

var resolve = {
    modules: [
        root,
        './website/static/vendor/bower_components',
        'node_modules',
    ],
    extensions: ['.*', '.es6.js', '.js', '.min.js', '.json'],
    // Need to alias libraries that aren't managed by bower or npm
    alias: {
        //use knockout-sortable v1.2.2 when wiki sort
        'knockout-sortable': staticPath('vendor/knockout-sortable/knockout-sortable-1.2.2.js'),
        'bootstrap-editable': staticPath('vendor/bootstrap-editable-custom/js/bootstrap-editable.js'),
        'jquery-blockui': staticPath('vendor/jquery-blockui/jquery.blockui.js'),
        'Caret.js': staticPath('vendor/bower_components/Caret.js/dist/jquery.caret.min.js'),
        'osf-panel': staticPath('vendor/bower_components/osf-panel/dist/jquery-osfPanel.min.js'),
        'clipboard': staticPath('vendor/bower_components/clipboard/dist/clipboard.js'),
        // Needed for knockout-sortable
        'jquery.ui.sortable': staticPath('vendor/bower_components/jquery-ui/ui/widgets/sortable.js'),
        // Needed for ace code editor in wiki
        'ace-noconflict': staticPath('vendor/bower_components/ace-builds/src-noconflict/ace.js'),
        'ace-ext-language_tools': staticPath('vendor/bower_components/ace-builds/src-noconflict/ext-language_tools.js'),
        'ace-mode-markdown': staticPath('vendor/bower_components/ace-builds/src-noconflict/mode-markdown.js'),
        'pagedown-ace-converter': addonsPath('wiki/static/pagedown-ace/Markdown.Converter.js'),
        'pagedown-ace-sanitizer': addonsPath('wiki/static/pagedown-ace/Markdown.Sanitizer.js'),
        'pagedown-ace-editor': addonsPath('wiki/static/pagedown-ace/Markdown.Editor.js'),
        'WikiPageMilkdown': addonsPath('wiki/static/wikiPageMilkdown.js'),
        'typo': staticPath('vendor/ace-plugins/typo.js'),
        'highlight-css': nodePath('highlight.js/styles/default.css'),
        'pikaday-css': nodePath('pikaday/css/pikaday.css'),
        // Also alias some internal libraries for easy access
        'addons': path.resolve(__dirname, 'addons'),
    },
    fallback: {
        fs: false,
        crypto: require.resolve('crypto-browserify'),
        buffer: require.resolve('buffer/'),
        path: require.resolve('path-browserify'),
        stream: require.resolve("stream-browserify"),
        vm: require.resolve("vm-browserify")
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
//    new webpack.optimization.splitChunks({ name: 'vendor', filename: 'vendor.js' }),
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

process.traceDeprecation = true

module.exports = {
    entry: entry,
    resolve: resolve,
    devtool: 'source-map',
    externals: externals,
    plugins: plugins,
    optimization: {
        splitChunks: {
            name: 'vendor',
            filename: 'vendor.[hash].js'
        }
    },
    output: output,
    module: {
        rules: [
            {test: /\.es6\.js$/, exclude: [/node_modules/, /bower_components/, /vendor/], loader: 'babel-loader'},
            {test: /\.css$/, use: [{loader: 'style-loader'}, {loader: 'css-loader'}]},
            // url-loader uses DataUrls; files-loader emits files
            {test: /\.png$/, use: [{loader: 'url-loader', options: {limit: 100000, mimetype : 'image/png'}}]},
            {test: /\.gif$/, use: [{loader: 'url-loader', options: {limit: 10000, mimetype : 'image/gif'}}]},
            {test: /\.jpg$/, use: [{loader: 'url-loader', options: {limit: 10000, mimetype : 'image/jpg'}}]},
            {test: /\.woff(2)?(\?v=[0-9]\.[0-9]\.[0-9])?$/, use: [{loader: 'url-loader', options: {mimetype : 'application/font-woff'}}]},
            {test: /\.svg/, use: [{loader: 'file-loader'}]},
            {test: /\.eot/, use: [{loader: 'file-loader'}]},
            {test: /\.ttf/, use: [{loader: 'file-loader'}]},
        ]
    }
};
