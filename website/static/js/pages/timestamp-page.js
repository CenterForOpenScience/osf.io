'use strict';

var $ = require('jquery');
var $osf = require('js/osfHelpers');
var node = window.contextVars.node;

var nodeApiUrl = window.contextVars.node.urls.api;
var project_file_list = window.contextVars.project_file_list;

$(document).ready(function(){
    var index = 0;
    for (var i = 0; i < project_file_list.length; i++) {
        var file_list = project_file_list[i].error_list;
        //console.log(file_list);
        var provider_tr = '<tr><td colspan="4">' + project_file_list[i].provider + '</td></tr>';
        $(provider_tr).appendTo($('#tree_timestamp_error_data'));
        for (var j = 0; j < file_list.length; j++) { 
                     var error_tr = '<tr>' +
                                    '<td class="addTimestamp">' +
                                    '<input type="checkBox" id="addTimestampCheck" value="' + index + '"/>&nbsp;' + 
                                    file_list[j].file_path + 
                                    '<input type="hidden" id="provider" value="' + project_file_list[i].provider + '" />' +
                                    '<input type="hidden" id="file_id" value="' + file_list[j].file_id + '" />' +
                                    '<input type="hidden" id="file_path" value="' + file_list[j].file_path + '" />' +
                                    '<input type="hidden" id="version" value="' + file_list[j].version + '" />' +
                                    '<input type="hidden" id="file_name" value="' + file_list[j].file_name + '" />' +
                                    '</td>' +
                                    '<td>' + file_list[j].operator_user + '</td>' +
                                    '<td>' + file_list[j].operator_date + '</td>' +
                                    '<td>' + file_list[j].verify_result_title + '</td>' +
                                    '</tr>';
                     //console.log(error_tr);
                     $(error_tr).appendTo($('#tree_timestamp_error_data'));
             index++;
        }
     }
});


