var $ = require('jquery');

var licenses = $.map(require('list-of-licenses'), function(value, key) {
    value.id = key;
    return value;
});

var DEFAULT_LICENSE = {
    id: 'NONE',
    name: 'None selected',
    text: 'Copyright {{year}} {{copyrightHolders}}',
    properties: ['year', 'copyrightHolders']
};
var OTHER_LICENSE = {
    id: 'OTHER',
    name: 'Other',
    text: 'Please see the "license.txt" uploaded in this project\'s OSF Storage'
};
licenses.unshift(DEFAULT_LICENSE);
licenses.push(OTHER_LICENSE);

module.exports = {
    list: licenses,
    DEFAULT_LICENSE: DEFAULT_LICENSE,
    OTHER_LICENSE: OTHER_LICENSE
};
    
