'use strict';

var $ = require('jquery');
var m = require('mithril');
var Treebeard = require('treebeard');
var citations = require('./citations');

var utils = {
    reduce: function(array, dst, fn){
	for (var i = 0;  i < array.length; i++){
	    fn(array[i], dst);
	}
	return dst;
    },
    zip: function(array1, array2){
	var zipped = [];
	var min = Math.min(array1.length, array2.length);
	for (var i = 0; i < min; i++){
	    zipped.push([array1[i], array2[i]]);
	}
	return zipped;
    }
};   

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
	    custom: function(item){
		return item.data.citation;
	    }
        }
    ];
};

var CitationGrid = function(selector, url) {
    var grid = this;

    var citationsApiUrl = window.contextVars.node.urls.api + 'mendeley/citations/';
    var styleRequest = $.get('/static/vendor/bower_components/styles/apa.csl');
    var citationsRequest = $.get(citationsApiUrl);
    $.when(styleRequest, citationsRequest).done(function(style, data) {

	var citation_list = utils.reduce(
	    data[0].map(
		function(item){
		    return item.csl;
		}
	    ), 
	    {}, 
	    function(item, dst){
		dst[item.id] = item;
	    });
        var citeproc = citations.makeCiteproc(style[0], citation_list, 'text');
        var bibliography = citeproc.makeBibliography();
	var filesData = utils.reduce(
	    utils.zip(bibliography[0].entry_ids, bibliography[1]), 
	    [], 
	    function(tup, dst){
		return dst.push({
		    id: tup[0][0],
		    citation: tup[1]
		});
	    }
	);
	var options = {
	    divID: selector.replace('#', ''),
	    filesData: filesData,
            columnTitles: getColumns,
            resolveRows: getRow
	};
	grid.treebeard = new Treebeard(options);	
    }).fail(function() {
        self.error('Could not load citations');
    });
};

module.exports = CitationGrid;
