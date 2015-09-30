var $ = require('jquery');

var licenses = require('list-of-licenses');
var list = $.map(licenses, function(value, key) {
    value.id = key;
    return value;
});

var DEFAULT_LICENSE = {
    id: 'NONE',
    name: 'No license',
    text: 'Copyright {{year}} {{copyrightHolders}}',
    properties: ['year', 'copyrightHolders']
};
var OTHER_LICENSE = {
    id: 'OTHER',
    name: 'License not listed - choose to add',
    text: 'Please see the "license.txt" uploaded in this project\'s OSF Storage'
};
list.unshift(DEFAULT_LICENSE);
list.push(OTHER_LICENSE);

var licenseGroups = [
    DEFAULT_LICENSE,
    {
        name: 'Content:',
        licenses: [licenses.CC0, licenses.CCBY]
    },
    {
        name: 'Code - Permissive:',
        licenses: [licenses.MIT, licenses.Apache2, licenses.BSD2, licenses.BSD3]
    },
    {
        name: 'Code - Copyleft:',
        licenses: [licenses.GPL3, licenses.GPL2]
    },
    {
        name: 'Code - Other:',
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
    
