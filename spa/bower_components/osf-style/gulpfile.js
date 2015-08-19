var gulp = require('gulp'),
    concat = require("gulp-concat"),
    minifyCSS = require('gulp-minify-css'),
    rename = require('gulp-rename'),
    uglify = require('gulp-uglify'),
    sass = require('gulp-ruby-sass'),
    livereload = require('gulp-livereload'),
    webserver = require('gulp-webserver'),
    autoprefixer = require('gulp-autoprefixer');


var paths = {
    cssfiles : [
        "./css/*.css"
    ],
    jsfiles : [
        "./bower_components/jquery/dist/*.min.js",
        "./bower_components/jquery-ui/*.min.js",
        "./bower_components/jquery-mockjax/*.js",
        "./bower_components/bootstrap/dist/js/*.min.js",
        "./js/script.js"
    ],
    sass : "sass/*.scss"
};

gulp.task('webserver', function() {
    gulp.src('./')
        .pipe(webserver({
            livereload: true,
            directoryListing: true,
            open: true
        }));
});

gulp.task('sass', function () {
    return sass('sass')
        .on('error', function (err) {
            console.error('Error!', err.message);
        })
        .pipe(autoprefixer('> 1%'))
        .pipe(gulp.dest('css'))
        .pipe(livereload());
});

gulp.task('default', ['webserver', 'sass', 'watch']);


gulp.task('watch', function () {
    livereload.listen();
    gulp.watch(paths.sass, ['sass']);
});