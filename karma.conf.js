module.exports = function (config) {
    config.set({
        browsers: ['Chrome'],
        frameworks: ['mocha'],
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
        webpack: {
            devtool: 'inline-source-map',
        },
        webpackServer: {
            noInfo: true // don't spam the console
        },
        plugins: [
            require('karma-webpack'),
            require('karma-mocha'),
            require('karma-sourcemap-loader'),
            require('karma-chrome-launcher'),
            require('karma-spec-reporter')
        ]
    });
};
