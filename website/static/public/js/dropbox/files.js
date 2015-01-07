webpackJsonp([28],{

/***/ 0:
/***/ function(module, exports, __webpack_require__) {

	__webpack_require__(43);


/***/ },

/***/ 43:
/***/ function(module, exports, __webpack_require__) {

	
	var m = __webpack_require__(13); 
	var Fangorn = __webpack_require__(5);

	function _fangornFolderIcons(item){
	    if(item.data.iconUrl){
	        return m('img',{src:item.data.iconUrl, style:{width:"16px", height:"auto"}}, ' ');
	    }
	    return undefined;
	}

	function _fangornLazyLoadError (item) {
	    item.notify.update('Dropbox couldn\'t load, please try again later.', 'deleting', undefined, 3000); 
	    return true;
	}

	Fangorn.config.dropbox = {
	    // Custom error message for when folder contents cannot be fetched
	    /*FETCH_ERROR: '<span class="text-danger">This Dropbox folder may ' +
	                    'have been renamed or deleted. ' +
	                    'Please select a folder at the settings page.</span>'*/
	                    // /static/addons/dropbox/comicon.png
	    folderIcon: _fangornFolderIcons,
	    lazyLoadError : _fangornLazyLoadError
	};




/***/ }

});