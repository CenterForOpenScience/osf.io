webpackJsonp([5],[
/* 0 */
/***/ function(module, exports, __webpack_require__) {

	/* WEBPACK VAR INJECTION */(function($) {var bootbox = __webpack_require__(9);

	$(document).ready(function() {

	    $('#githubAddKey').on('click', function() {
	        window.location.href = '/api/v1/settings/github/oauth/';
	    });

	    $('#githubDelKey').on('click', function() {
	        bootbox.confirm({
	            title: 'Remove access key?',
	            message: 'Are you sure you want to remove your GitHub access key? This will ' +
	                'revoke access to GitHub for all projects you have authorized ' +
	                'and delete your access token from GitHub. Your OSF collaborators ' +
	                'will not be able to write to GitHub repos or view private repos ' +
	                'that you have authorized.',
	            callback: function(result) {
	                if(result) {
	                    $.ajax({
	                        url: '/api/v1/settings/github/oauth/',
	                        type: 'DELETE',
	                        success: function() {
	                            window.location.reload();
	                        }
	                    });
	                }
	            }
	        });
	    });
	});
	/* WEBPACK VAR INJECTION */}.call(exports, __webpack_require__(13)))

/***/ }
]);