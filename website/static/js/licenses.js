var $ = require('jquery');

var licenses = $.map(require('list-of-licenses'), function(value, key) {
    value.id = key;
    var properties = value.properties || [];
    var newProperties = {};
    $.each(properties, function(i, prop) {
        var words = prop.split(' ');
        words[0] = words[0].slice(0, 1).toLowerCase() + words[0].slice(1);        
        newProperties[words.join('')] = {
            label: prop            
        };
    });
    value.properties = newProperties;
    return value;
});

var DEFAULT_LICENSE = {
    id: 'NONE',
    name: 'None selected',
    text: 'Copyright {{year}} {{copyrightHolders}}',
    properties: {
        year: {
            label: 'Year'
        },
        copyrightHolders: {
            label:' Copyright Holders'
        }
    }
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
    
