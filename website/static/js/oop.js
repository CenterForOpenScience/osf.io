// These are mostly a simplification of
// augment.js (https://github.com/javascript/augment, MIT Licensed) and
// Douglas Crockford's protoypical inheritance pattern.
require('js/objectCreateShim'); // IE8 compat


/**
 * Usage:
 *
 *  var Animal = defclass({
 *      constructor: function(name) {
 *          this.name = name || 'unnamed';
 *          this.sleeping = false;
 *      },
 *      sayHi: function() {
 *          console.log('Hi, my name is ' + this.name);
 *      }
 *  });
 */
function defclass(prototype) {
    var constructor = prototype.hasOwnProperty('constructor') ? prototype.constructor : function() {};
    constructor.prototype = prototype;
    return constructor;
}

/**
 * Usage:
 *
 *  var Person = extend(Animal, {
 *      constructor: function(name) {
 *          this.super.constructor.call(name);
 *          this.name = name || 'Steve';
 *      }
 *  });
 */
function extend(cls, sub) {
    var prototype = Object.create(cls.prototype);
    for (var key in sub) { prototype[key] = sub[key]; }
    prototype.super = cls.prototype;
    return defclass(prototype);
}

module.exports = {
    defclass: defclass,
    extend: extend
};
