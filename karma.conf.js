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
    resolve: webpackCommon.resolve
};


module.exports = function (config) {
    config.set({
        browsers: ['Chrome'],
        frameworks: ['mocha', 'sinon'],
        files: [
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
        },
        plugins: [
            require('karma-webpack'),
            require('karma-mocha'),
            require('karma-sourcemap-loader'),
            require('karma-chrome-launcher'),
            require('karma-spec-reporter'),
            require('karma-sinon')
        ]
    });
};
