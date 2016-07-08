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
var InstitutionImg = {
    view: function(ctrl, opts) {
        if (opts.width && !opts.height) { opts.height = opts.width; }
        if (opts.height && !opts.width) { opts.width = opts.height; }
        var logoPath = required(opts, 'logoPath');
        var institutionName = required(opts, 'name');
        var imgOpts = $.extend({}, opts, {
            className: 'img-circle ' + (opts.className || ''),
            style: opts.style,
            src: logoPath,
            width: opts.width, height: opts.height,
            alt: opts.alt || institutionName,
            title: opts.title || institutionName
        });
        return m('img', imgOpts);
    }
};

var SelectableInstitution = {
    view: function(ctrl, opts) {
        var checked = required(opts, 'checked');
        var mutedStyle = {
            cursor: 'pointer',
            opacity: '0.25',
            '-webkit-filter': 'grayscale(100%)',
            filter: 'grayscale(100%)'
        };
        if (!checked) {
            opts.style = $.extend({}, mutedStyle, opts.style);
        }
        return m.component(InstitutionImg, opts);
    }
};

module.exports = {
    InstitutionImg: InstitutionImg,
    SelectableInstitution: SelectableInstitution,
};
