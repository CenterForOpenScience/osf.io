(function (global, factory) {
  if (typeof define === 'function' && define.amd) {  // AMD/RequireJS
    define(['jquery'], factory);
  } else if (typeof module === 'object') {  // CommonJS/Node
    module.exports = factory(jQuery);
  } else {  // No module system
    global.HGrid = factory(jQuery);
  }
}(this, function(jQuery) {
