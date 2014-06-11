var gulp = require('gulp');

var uglify = require('gulp-uglify');
var rename = require('gulp-rename');
var qunit = require('node-qunit-phantomjs');
var concat = require('gulp-concat');
var jshint = require('gulp-jshint');

var RELEASE_NAME = 'hgrid-draggable.js';
var RELEASE_MIN_NAME = 'hgrid-draggable.min.js';


var BUILD_ACTIONS = ['concat', 'compress'];
var WATCH_ACTIONS = ['concat', 'test', 'lint'];
var DEFAULT_ACTIONS = ['concat', 'compress', 'test', 'lint'];

gulp.task('test', function() {
  qunit('./tests/index.html', {verbose: true});
});

// Concatenate files
// Slickgrid files are bundled
gulp.task('concat', function() {
  gulp.src(['amd-header.js', 'src/vendor/*.js', 'src/*.js', 'amd-footer.js'])
    .pipe(concat(RELEASE_NAME))
    .pipe(gulp.dest('.'));
});

gulp.task('lint', function() {
  return gulp.src(RELEASE_NAME)
    .pipe(jshint())
    .pipe(jshint.reporter('jshint-stylish'));
});

gulp.task('compress', function() {
  return gulp.src(RELEASE_NAME)
    .pipe(uglify())
    .pipe(rename(RELEASE_MIN_NAME))
    .pipe(gulp.dest('.'));
});

gulp.task('watch', function () {
  gulp.watch('src/**/*.js', [WATCH_ACTIONS]);
  gulp.watch('tests/*.js', [WATCH_ACTIONS]);
});

gulp.task('build', BUILD_ACTIONS);
gulp.task('default', DEFAULT_ACTIONS);
