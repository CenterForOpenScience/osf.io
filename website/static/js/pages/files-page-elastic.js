'use strict';

var $ = require('jquery');
var $osf = require('js/osfHelpers');
var Fangorn = require('js/fangorn');
var m = require('mithril');

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
            filterTemplate: function () {
                var tb = this;
                return m('input.pull-right.form-control[placeholder=\'' + tb.options.filterPlaceholder + '\'][type=\'text\']', {
                    style: 'width:100%;display:inline;',
                    oninput: tb.filter,
                    value: tb.filterText()
                });
            },
            onfilter: function(){
                var queryElasticSearch = function(query, node_id){
                    var data = {'q': query, 'pid': node_id};
                    var response = $.getJSON('/api/v1/project_files', data);
                    return response;
                };

                var showResults = function(paths, tb){

                    // convert to a dictionary for constant time look-ups.
                    var path_dict = {};
                    for (var i=0; i<paths.length; i++){
                        path_dict[paths[i]] = true;
                    }

                    // remove all displayed items
                    tb.visibleIndexes = [];

                    // add items matching filter or in elastic search to displayed.
                    for (var j=0; j < tb.flatData.length; j++){
                        var element = tb.flatData[j];
                        var item = tb.find(element.id);
                        if (tb.rowFilterResult(item)) {
                            tb.visibleIndexes.push(j);
                        }
                        else if (element.row.kind === 'file'){
                            var path = element.row.path.replace('/', '');
                            if (path_dict[path]){
                                tb.visibleIndexes.push(j);
                            }
                        }
                    }
                    tb.calculateHeight();
                    tb.refreshRange(0);
                };

                var tb = this;
                var query = this.filterText();
                var node_id = tb.flatData[0].row.nodeID;
                var response = queryElasticSearch(query, node_id).done(
                    function(results){showResults(results, tb);}
                );
            }
        });
    });
});
