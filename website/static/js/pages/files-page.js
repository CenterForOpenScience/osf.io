'use strict';

var $ = require('jquery');
var $osf = require('js/osfHelpers');
var Fangorn = require('js/fangorn');
var m = require('mithril');

// Don't show dropped content if user drags outside grid
window.ondragover = function(e) { e.preventDefault(); };
window.ondrop = function(e) { e.preventDefault(); };

var nodeApiUrl = window.contextVars.node.urls.api;

var showResults = function(result_paths, tb){
    tb.visibleIndexes = [];
    for (var i=0; i < tb.flatData.length; i++){
        var element = tb.flatData[i];
        if (element.row.kind === "file"){
            var path = element.row.path.replace("/", "");
            if (result_paths.indexOf(path) !== -1){
                tb.visibleIndexes.push(i);
            }
        }
    }
    tb.refreshRange(0);
};

var queryElasticSearch = function(query, tb){
    var data = {"q": query, "pid": "ykcxq"};
    $.getJSON("/api/v1/project_files", data, function(paths){ showResults(paths, tb)});
};

var fileFilter = function(tb){
    var filter = tb.filterText().toLowerCase(),
        index = tb.visibleTop;
    if (filter.length === 0) {
        tb.resetFilter();
    } else {
        if (!tb.filterOn) {
            tb.filterOn = true;
            tb.lastNonFilterLocation = tb.lastLocation;
        }
        if (!tb.visibleTop) {
            index = 0;
        }
        queryElasticSearch(filter, tb);
    }
};

var filterTemplate = function () {
    var tb = this;
    return m("input.pull-right.form-control[placeholder='" + tb.options.filterPlaceholder + "'][type='text']", {
        style: "width:100%;display:inline;",
        onkeyup: function (e){
            m.withAttr("value", tb.filterText)(e);
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
            filterTemplate: filterTemplate,
            hiddenFilterRows : ['path'],
        });
    });
});
