webpackJsonp([14],{

/***/ 0:
/***/ function(module, exports, __webpack_require__) {

	__webpack_require__(42);


/***/ },

/***/ 42:
/***/ function(module, exports, __webpack_require__) {

	/* WEBPACK VAR INJECTION */(function($) {/**
	 * Github FileBrowser configuration module.
	 */

	var Rubeus = __webpack_require__(3);

	// Private members

	function refreshGitHubTree(grid, item, branch) {
	    var data = item.data || {};
	    data.branch = branch;
	    var url = item.urls.branch + '?' + $.param({branch: branch});
	    $.ajax({
	        type: 'get',
	        url: url
	    }).done(function(response) {
	        // Update the item with the new branch data
	        $.extend(item, response[0]);
	        grid.reloadFolder(item);
	    });
	}

	// Register configuration
	Rubeus.cfg.github = {
	    // Handle changing the branch select
	    listeners: [{
	        on: 'change',
	        selector: '.github-branch-select',
	        callback: function(evt, row, grid) {
	            var $this = $(evt.target);
	            var branch = $this.val();
	            refreshGitHubTree(grid, row, branch);
	        }
	    }]
	};

	// Define HGrid Button Actions
	HGrid.Actions['githubDownloadZip'] = {
	    on: 'click',
	    callback: function (evt, row) {
	        var url = row.urls.zip;
	        window.location = url;
	    }
	};

	HGrid.Actions['githubVisitRepo'] = {
	    on: 'click',
	    callback: function (evt, row) {
	        var url = row.urls.repo;
	        window.location = url;
	    }
	};


	
	/* WEBPACK VAR INJECTION */}.call(exports, __webpack_require__(13)))

/***/ }

});