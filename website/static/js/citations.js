'use strict';

require('../css/citations.css');
var locale = require('raw!../vendor/bower_components/locales/locales-en-US.xml');

var makeCiteproc = function(style, citations, format) {
    format = format || 'html';
    var sys = {
        retrieveItem: function(id) {
            return citations[id];
        },
        retrieveLocale: function() {
            return locale;
        }
    };
    var citeproc = new CSL.Engine(sys, style); // jshint ignore:line
    citeproc.setOutputFormat(format);
    citeproc.appendCitationCluster({
        citationItems: Object.keys(citations).map(function(key) {
            return {
                id: key
            };
        }),
        properties: {
            noteIndex: 0
        }
    });
    return citeproc;
};

module.exports = {
    makeCiteproc: makeCiteproc
};
