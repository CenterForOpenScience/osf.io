var webpack = require('webpack');

module.exports = {
    entry: {
        profile: './website/static/js/app/profile.js',
        project: './website/static/js/app/project.js',
        dashboard: './website/static/js/app/dashboard.js'
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
            'knockout-punches': '../vendor/knockout-punches/knockout.punches.min.js',
            'knockout-sortable': '../vendor/knockout-sortable/knockout-sortable.js',
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
