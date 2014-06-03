var gulp = require('gulp');

var uglify = require('gulp-uglify');
var rename = require('gulp-rename');
var qunit = require('gulp-qunit');
var concat = require('gulp-concat');

var RELEASE_NAME = 'hgrid-draggable.js';
var RELEASE_MIN_NAME = 'hgrid-draggable.min.js';


var WATCH_ACTIONS = ['concat', 'test'];
var DEFAULT_ACTIONS = ['concat', 'compress', 'test'];

gulp.task('test', function() {
  gulp.src('./tests/index.html')
    .pipe(qunit());
});

// Concatenate files
// Slickgrid files are bundled
gulp.task('concat', function() {
  gulp.src(['amd-header.js', 'src/vendor/*.js', 'src/*.js', 'amd-footer.js'])
    .pipe(concat(RELEASE_NAME))
    .pipe(gulp.dest('.'));
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

gulp.task('default', DEFAULT_ACTIONS);
