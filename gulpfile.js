'use strict';

var gulp = require('gulp');
var gutil = require('gulp-util');
var webpack = require('webpack');
var del = require('del');

var webpackConf = require('./webpack.config.js');

gulp.task('clean', function(callback) {
  del([webpackConf.output.path], callback);
});

// Webpack dev settings
var webpackDevConf = Object.create(webpackConf);
webpackDevConf.debug = true;


// Webpack prod settings
var webpackProdConf = Object.create(webpackConf);
webpackProdConf.debug = false;
webpackProdConf.plugins = webpackConf.plugins.concat([
  // minify in production
  new webpack.optimize.UglifyJsPlugin()
]);

var execWebpack = function(config, taskName, callback) {
  webpack(config, function(err, stats) {
    if (err) {
      throw new gutil.PluginError(taskName, err);
    }
    gutil.log('[' + taskName + ']', stats.toString({colors: true}));
    callback();
  });
};

gulp.task('webpack:dev', function(callback) {
  execWebpack(webpackDevConf, 'webpack:dev', callback);
});

gulp.task('webpack:prod', function(callback) {
  execWebpack(webpackProdConf, 'webpack:prod', callback);
});

gulp.task('watch', ['clean'], function() {
  gulp.watch('./website/static/js/**/*', ['webpack:dev']);
});

gulp.task('build', ['clean'], function() {
  gulp.start(['webpack:dev']);
});

gulp.task('default', ['build']);
