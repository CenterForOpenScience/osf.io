webpackJsonp([41],[
/* 0 */
/***/ function(module, exports, __webpack_require__) {

'use strict';

var $osf = __webpack_require__(47);
var $ = __webpack_require__(38);

// model for components, due to simplicity did not create a new file
var ComponentControl = {};

// binds to component scope in render_nodes.mako
$('.render-nodes-list').each(function() {
    $osf.applyBindings(ComponentControl, this);
});



/***/ }
]);
//# sourceMappingURL=render-nodes.js.map