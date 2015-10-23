webpackJsonp([15],[
/* 0 */
/***/ function(module, exports, __webpack_require__) {

'use strict';

var $ = __webpack_require__(38);
var $osf = __webpack_require__(47);
var Fangorn = __webpack_require__(186);

// Don't show dropped content if user drags outside grid
window.ondragover = function(e) { e.preventDefault(); };
window.ondrop = function(e) { e.preventDefault(); };

var nodeApiUrl = window.contextVars.node.urls.api;

$(document).ready(function(){
    $.ajax({
      url: nodeApiUrl + 'files/grid/'
    }).done(function(data) {
        new Fangorn({
            placement: 'project-files',
            divID: 'treeGrid',
            filesData: data.data,
            xhrconfig: $osf.setXHRAuthorization
        });
    });
});


/***/ }
]);
//# sourceMappingURL=files-page.js.map