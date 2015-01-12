var common = require('./webpack.common.config.js');

module.exports = {
    // Split code chunks by page
    entry: common.entry,
    resolve: common.resolve,
    externals: common.externals,
    debug: true,
    output: {
        path: './website/static/public/js/',
        // publicPath: '/static/', // used to generate urls to e.g. images
        filename: '[name].js'
    },
    watch: true,
    devtool: 'source-map',
    plugins: common.plugins
};
