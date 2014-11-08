var webpack = require('webpack');

module.exports = {
  // This is the main file that should include all other JS files
  entry: {
    profile: './website/static/js/app/profile.js',
    project: './website/static/js/app/project.js'
  },
  debug: true,
  output: {
    path: './website/static/public/js/',
    // publicPath: '/static/', // used to generate urls to e.g. images
    // If you want to generate a filename with a hash of the content (for cache-busting)
    // filename: "main-[hash].js",
    filename: '[name].js'
  },
  resolve: {
    // Tell webpack to look for required files in bower and node
    modulesDirectories: ['./website/static/vendor/bower_components', 'node_modules'],
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
    new webpack.ResolverPlugin(
        new webpack.ResolverPlugin.DirectoryDescriptionFilePlugin("bower.json", ["main"])
    )
  ],
  externals: {
      // require("jquery") is external and available
      //  on the global var jQuery
      // 'jquery': "jQuery"
  }
};
