// These are mostly a simplification of
// augment.js (https://github.com/javascript/augment, MIT Licensed) and
// Douglas Crockford's protoypical inheritance pattern.

var noop = function() {};

// IE8 shim for Object.create
if (typeof Object.create !== 'function') {
    Object.create = function (o) {
        noop.prototype = o;
        return new noop();
    };
}

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
    var constructor = prototype.hasOwnProperty('constructor') ? prototype.constructor : noop;
    constructor.prototype = prototype;
    return constructor;
}

/**
 * Usage:
 *
 *     var Person = extend(Animal, {
 *         constructor: function(name) {
 *             this.super.constructor(name);
 *             this.name = name || 'Steve';
 *         }
 *     });
 */
function extend(constructor, sub) {
    var prototype = Object.create(constructor.prototype);
    for (var key in sub) { prototype[key] = sub[key]; }
    prototype.super = constructor.prototype;
    return defclass(prototype);
}

module.exports = {
    defclass: defclass,
    extend: extend
};
