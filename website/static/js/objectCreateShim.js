/**
 * IE8 shim for Object.create. Should be imported whenever Object.create is used.
 */
if (typeof Object.create !== 'function') {
    Object.create = function (o) {
        var F = function() {};
        F.prototype = o;
        return new F();
    };
}
