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
            className: 'img-circle',
            src: logoPath,
            width: opts.width, height: opts.height
        })
    }
}


var CheckableInst = {
    view: function(ctrl, opts) {
        var checked = required(opts.checked);
        return m('',[
            m.component(InstitutionImage, opts),
            checked ?
            m('i.img-circle.fa.fa-check',
                {
                    style: {
                        color: '#C7FFC7',
                        textAlign: 'center',
                        fontSize: '275%',
                        width: '100%', height: '100%',
                        top: '0', left: '0',
                        position: 'absolute',
                        display: 'block',
                        background: 'rgba(0, 0, 0, .4)'
                    }
                }
            ) : '',
        ])
    }
}



module.exports = {
    InstitutionImage: InstitutionImage,
    CheckableInst: CheckableInst,
};
