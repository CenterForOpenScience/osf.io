var webpack = require('webpack');

module.exports = {
    entry: {
        dashboard: './website/static/js/pages/dashboard.js',
        profile: './website/static/js/pages/profile.js'
    },
    debug: true,
    output: {
        path: './website/static/public/js/',
        // publicPath: '/static/', // used to generate urls to e.g. images
        filename: '[name].js'
    },
    resolve: {
        // Look for required files in bower and node
        modulesDirectories: ['./website/static/vendor/bower_components', 'node_modules'],
        alias: {
            // Alias libraries that aren't managed by bower or npm
            'knockout-punches': '../vendor/knockout-punches/knockout.punches.min.js',
            'knockout-sortable': '../vendor/knockout-sortable/knockout-sortable.js',
            'knockout-validation': '../vendor/knockout-validation/knockout.validation.min.js',
            'bootbox': '../vendor/bootbox/bootbox.min.js'
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
