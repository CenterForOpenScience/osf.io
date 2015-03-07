var webpack = require('webpack');
// TODO: use BowerWebpackPlugin
// var BowerWebpackPlugin = require('bower-webpack-plugin');
var webpackCommon = require('./webpack.common.config.js');

// Put in separate file?
var webpackTestConfig = {
    devtool: 'inline-source-map',
    plugins: [
       new webpack.ResolverPlugin(
            new webpack.ResolverPlugin.DirectoryDescriptionFilePlugin('bower.json', ['main'])
        ),

        new webpack.ProvidePlugin({
            $: 'jquery',
            jQuery: 'jquery',
            'window.jQuery': 'jquery',
            'window.$': 'jquery'
        }),
    ],
    resolve: webpackCommon.resolve,
    externals: {'jquery': 'jQuery', 'jquery-ui': 'jQuery.ui'},
    module: {
        loaders: [
            // Assume test files are ES6
            {test: /\.test\.js$/, loader: 'babel-loader'},
        ]
    }
};


module.exports = function (config) {
    config.set({
        browsers: ['PhantomJS'],
        frameworks: ['mocha', 'sinon'],
        files: [
            'website/static/vendor/bower_components/jquery/dist/jquery.js',
            'website/static/vendor/bower_components/jquery-ui/ui/jquery-ui.js',
            // Only need to target one file, which will load all files in tests/ that
            // match *.test.js
            'website/static/js/tests/tests.webpack.js',
        ],
        reporters: ['spec'],
        preprocessors: {
            // add webpack as preprocessor
            'website/static/js/tests/tests.webpack.js': ['webpack', 'sourcemap'],
        },
        webpack: webpackTestConfig,
        webpackServer: {
            noInfo: true // don't spam the console
        }
    });
};
