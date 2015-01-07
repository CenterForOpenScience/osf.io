webpackJsonp([21],{

/***/ 0:
/***/ function(module, exports, __webpack_require__) {

	__webpack_require__(58);

/***/ },

/***/ 58:
/***/ function(module, exports, __webpack_require__) {

	/**
	 * Created by faye on 11/6/14.
	 */
	var m = __webpack_require__(13); 

	var Fangorn = __webpack_require__(5);


	function _fangornFolderIcons(item){
	    if(item.data.addonFullname){
	        //This is a hack, should probably be changed...
	        return m('img',{src:item.data.iconUrl, style:{width:"16px", height:"auto"}}, ' ');
	    }
	}

	Fangorn.config.s3 = {
	    folderIcon: _fangornFolderIcons,
	};




/***/ }

});