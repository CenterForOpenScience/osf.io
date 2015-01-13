var common = require('./webpack.common.config.js');

module.exports = {
    // Split code chunks by page
    entry: common.entry,
    resolve: common.resolve,
    externals: common.externals,
    output: common.output,
    debug: true,
    watch: true,
    devtool: 'source-map',
    plugins: common.plugins
};
