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
