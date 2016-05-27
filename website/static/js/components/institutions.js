'use strict';
var m  = require('mithril');

// TODO: Put me in a utils file
function required(opt) {
    if (opt == null || opt === undefined) {
        throw new Error('Missing required option');
    }
    return opt;
}


var InstitutionImage = {
    view: function(ctrl, options) {
        var defaults = {
            width: '40px', height: '40px'
        };
        var opts = $.extend({}, defaults, options);
        var logoPath = required(opts.logoPath);
        return m('img', {
            className: 'img-circle text-muted',
            src: logoPath,
            width: opts.width, height: opts.height
        })
    }
}


var CheckableInst = {
    view: function(ctrl, opts) {
        var checked = required(opts.checked);
        return [
            m.comp(Institution, opts),
            checked ? m.comp(Checkmark): ''
        ]
    }
}



module.exports = {
    InstitutionImage: InstitutionImage
};
