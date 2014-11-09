var path = require('path');
var webpack = require('webpack');
var root = path.join(__dirname, 'website', 'static');
/** Return the absolute path given a path relative to ./website/static */
var fromRoot = function(dir) {
    return path.join(root, dir);
};
module.exports = {
    // Split code chunks by page
    entry: {
        dashboard: './website/static/js/pages/dashboard-page.js',
        profile: './website/static/js/pages/profile-page.js'
    },
    debug: true,
    output: {
        path: './website/static/public/js/',
        // publicPath: '/static/', // used to generate urls to e.g. images
        filename: '[name].js'
    },
    resolve: {
        root: root,
        // Look for required files in bower and node
        modulesDirectories: ['./website/static/vendor/bower_components', 'node_modules'],
        alias: {
            // Alias libraries that aren't managed by bower or npm
            'knockout-punches': fromRoot('/vendor/knockout-punches/knockout.punches.min.js'),
            'knockout-sortable': fromRoot('/vendor/knockout-sortable/knockout-sortable.js'),
            'knockout-validation': fromRoot('/vendor/knockout-validation/knockout.validation.min.js'),
            'bootbox': fromRoot('/vendor/bootbox/bootbox.min.js'),
            // Needed for knockout-sortable
            'jquery.ui.sortable': fromRoot('/vendor/bower_components/jquery-ui/ui/jquery.ui.sortable.js'),
            // Dropzone monkeypatching needed for signed URL uploads
            'dropzone-patch': fromRoot('js/dropzone-patch.js')
        }
    },
    module: {
        loaders: [
            { test: /\.css/, loader: 'style-loader!css-loader' },
            { test: /\.gif/, loader: 'url-loader?limit=10000&minetype=image/gif' },
            { test: /\.jpg/, loader: 'url-loader?limit=10000&minetype=image/jpg' },
            { test: /\.png/, loader: 'url-loader?limit=10000&minetype=image/png' }
        ]
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
            jQuery: 'jquery',
            ko: 'knockout'
        }),
        // Slight hack to make sure that CommonJS is always used
        new webpack.DefinePlugin({
            'define.amd': false
        })
    ],
    externals: {
        // require("jquery") is external and available
        //  on the global var jQuery
        'jquery': 'jQuery',
        'jquery-ui': 'jQuery.ui'
    }
};
