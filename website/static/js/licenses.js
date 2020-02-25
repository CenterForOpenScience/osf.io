var $ = require('jquery');

var licenses = require('json-loader!@centerforopenscience/list-of-licenses');
delete licenses.AFL3;

var rdmGettext = require('js/rdmGettext');
var gt = rdmGettext.rdmGettext();
var _ = function(msgid) { return gt.gettext(msgid); };

var DEFAULT_LICENSE, OTHER_LICENSE;
var list = $.map(licenses, function(value, key) {
    value.id = key;

    if (value.id === 'NONE'){
        DEFAULT_LICENSE = value;
        value.name = '_(' + value.name + ')';
    }
    if (value.id === 'OTHER'){
        OTHER_LICENSE = value;
        value.name = '_(' + value.name + ')';
    }

    return value;
});

var licenseGroups = [
    DEFAULT_LICENSE,
    {
        name: _('Content:'),
        licenses: [licenses.CC0, licenses.CCBY]
    },
    {
        name: _('Code - Permissive:'),
        licenses: [licenses.MIT, licenses.Apache2, licenses.BSD2, licenses.BSD3]
    },
    {
        name: _('Code - Copyleft:'),
        licenses: [licenses.GPL3, licenses.GPL2]
    },
    {
        name: _('Code - Other:'),
        licenses: [licenses.Artistic2, licenses.Eclipse1, licenses.LGPL3, licenses.LGPL2_1, licenses.Mozilla2]
    },
    OTHER_LICENSE
];

module.exports = {
    list: list,
    DEFAULT_LICENSE: DEFAULT_LICENSE,
    OTHER_LICENSE: OTHER_LICENSE,
    groups: licenseGroups
};
