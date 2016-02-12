'use strict';

var $ = require('jquery');
var $osf = require('js/osfHelpers');
var Fangorn = require('js/fangorn');
var m = require('mithril');

var ENTER_KEY = 13;

// Don't show dropped content if user drags outside grid
window.ondragover = function(e) { e.preventDefault(); };
window.ondrop = function(e) { e.preventDefault(); };

var nodeApiUrl = window.contextVars.node.urls.api;


// Only display files with a path in a given array.
var showResults = function(result_paths, tb){
    tb.visibleIndexes = [];
    for (var i=0; i < tb.flatData.length; i++){
        var element = tb.flatData[i];
        var item = tb.find(element.id);
        if (tb.rowFilterResult(item)) {
            tb.visibleIndexes.push(i);
        }
        else if (element.row.kind === 'file'){
            var path = element.row.path.replace('/', '');
            if (result_paths.indexOf(path) !== -1){
                tb.visibleIndexes.push(i);
            }
        }
    }
    tb.refreshRange(0);
    m.redraw(true);
};


// Query elastic-search for a list of matching paths.
var queryElasticSearch = function(query, node_id){
    var data = {'q': query, 'pid': node_id};
    var response = $.getJSON('/api/v1/project_files', data);
    return response;
};


// Filter the files page using current query.
var fileFilter = function(tb){
    var filter = tb.filterText().toLowerCase(),
        index = tb.visibleTop;
    if (filter.length === 0) {
        tb.resetFilter();
    }
    else {
        if (!tb.filterOn) {
            tb.filterOn = true;
            tb.lastNonFilterLocation = tb.lastLocation;
        }
        if (!tb.visibleTop) {
            index = 0;
        }
        $.getJSON('api/v2/project_files', {'q': filter, 'pid': tb.flatData[0].row.nodeID}).done(
            function(results){}
        )
        var response = queryElasticSearch(filter, tb.flatData[0].row.nodeID);
        response.done(function(paths){showResults(paths, tb);});
    }
};


// Replace the default filter template with one using elastic search.
var filterTemplate = function () {
    var tb = this;
    return m('input.pull-right.form-control[placeholder=\'' + tb.options.filterPlaceholder + '\'][type=\'text\']', {
        style: 'width:100%;display:inline;',
        onkeyup: function (e){
            m.withAttr('value', tb.filterText)(e);
            fileFilter(tb);
        },
        value: tb.filterText()
    });
};


$(document).ready(function(){
    $.ajax({
      url: nodeApiUrl + 'files/grid/'
    }).done(function(data) {
        new Fangorn({
            placement: 'project-files',
            divID: 'treeGrid',
            filesData: data.data,
            xhrconfig: $osf.setXHRAuthorization,
            onfilter: function(){
                var showResults = function(paths, tb){
                    tb.visibleIndexes = [];
                    for (var i=0; i < tb.flatData.length; i++){
                        var element = tb.flatData[i];
                        var item = tb.find(element.id);
                        if (tb.rowFilterResult(item)) {
                            tb.visibleIndexes.push(i);
                        }
                        else if (element.row.kind === 'file'){
                            var path = element.row.path.replace('/', '');
                            if (paths.indexOf(path) !== -1){
                                tb.visibleIndexes.push(i);
                            }
                        }
                    }
                    tb.refreshRange(0);
                    m.redraw(true);
                };

                var queryElasticSearch = function(query, node_id){
                    var data = {'q': query, 'pid': node_id};
                    var response = $.getJSON('/api/v1/project_files', data);
                    return response;
                };

                var tb = this;
                var query = this.filterText;
                var node_id = tb.flatData[0].row.nodeID;
                console.log(query);
                var response = queryElasticSearch(query, node_id).done(
                    function(results){showResults(results, tb);}
                )


            }
        });
    });
});
