/**
* Mithril components for OSF4I.
*/
'use strict';
var $ = require('jquery');
var m = require('mithril');

var utils = require('js/components/utils');
var required = utils.required;

/**
 * Display an OSF4I logo.
 */
var MUTED_OPACITY = '0.5';
var InstitutionImg = {
    view: function(ctrl, opts) {
        if (!opts.width && !opts.height) {
            throw new Error('InstitutionImg requires width and/or height option.');
        }
        if (opts.width && !opts.height) { opts.height = opts.width; }
        if (opts.height && !opts.width) { opts.width = opts.height; }
        var logoPath = required(opts, 'logoPath');
        var institutionName = required(opts, 'name');
        var style = {};
        if (opts.muted) {
            style.opacity = MUTED_OPACITY;
        }
        // allow user to pass additional styles
        style = $.extend({}, style, opts.style);
        var imgOpts = $.extend({}, opts, {
            className: 'img-circle text-muted ' + (opts.className || ''),
            style: style,
            src: logoPath,
            width: opts.width, height: opts.height,
            alt: opts.alt || institutionName
        });
        return m('img', imgOpts);
    }
};

var CheckableInstitution = {
    view: function(ctrl, opts) {
        var checked = required(opts, 'checked');
        return m('',[
            m.component(InstitutionImg, opts),
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
        ]);
    }
};

module.exports = {
    InstitutionImg: InstitutionImg,
    CheckableInstitution: CheckableInstitution,
};
