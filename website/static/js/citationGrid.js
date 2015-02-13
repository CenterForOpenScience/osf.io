'use strict';

var m = require('mithril');
var Treebeard = require('treebeard');

var getColumns = function() {
    return [
        {
            title: 'Citation',
            sort: false
        }
    ];
};

var getRow = function(item) {
    return [
        {
            data: 'csl',
            custom: function() {
                return m('span', JSON.stringify(item.csl));
            }
        }
    ];
};

var CitationGrid = function(selector, url) {
    var options = {
        columnTitles: getColumns,
        resolveRows: getRow
    };
    this.treebeard = new Treebeard(options);
};

module.exports = CitationGrid;
