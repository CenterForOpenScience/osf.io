/**
 *
 */

var webpack = require('webpack');
var webpackCommon = require('./webpack.common.config.js');

// A subset of the app webpack config
var webpackTestConfig = {
    devtool: 'inline-source-map',
    plugins: [
        new webpack.ResolverPlugin(
            new webpack.ResolverPlugin.DirectoryDescriptionFilePlugin('bower.json', ['main'])
        ),

        // Make sure that CommonJS is always used
        new webpack.DefinePlugin({
            'define.amd': false
        }),

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
        loaders: webpackCommon.module.loaders.concat([
            // Assume test files are ES6
            {test: /\.test\.js$/, loader: 'babel-loader'},
        ])
    },
        node: {
       fs: 'empty'
    }
};

module.exports = {
    frameworks: ['mocha', 'sinon'],
    files: [
        // Mimics loading jquery and jquery-ui with script tags
        'website/static/vendor/bower_components/jquery/dist/jquery.js',
        'website/static/vendor/bower_components/jquery-ui/jquery-ui.js',
        'website/static/vendor/bower_components/bootstrap/dist/js/bootstrap.js',
        // Only need to target one file, which will load all files in tests/ that
        // match *.test.js, including addons tests
        'website/static/js/tests/tests.webpack.js',
    ],
    preprocessors: {
        // add webpack as preprocessor
        'website/static/js/tests/tests.webpack.js': ['webpack', 'sourcemap'],
    },
    webpack: webpackTestConfig,
    webpackMiddleware: {noInfo: true},
    webpackServer: {
        noInfo: true // don't spam the console
    },

    // Avoid DISCONNECTED messages
    // See https://github.com/karma-runner/karma/issues/598
    browserDisconnectTimeout : 100000, // default 2000
    browserDisconnectTolerance : 1, // default 0
    browserNoActivityTimeout : 600000 //default 10000
};
