'use strict';

var $ = require('jquery');
var $osf = require('js/osfHelpers');
var node = window.contextVars.node;

var nodeApiUrl = window.contextVars.node.urls.api;
var project_file_list = window.contextVars.project_file_list;

$(document).ready(function(){
//    var project_tr = '<tr><td colspan="4">' + node.title + '</td></tr>';
//    $(project_tr).appendTo($('#tree_timestamp_error_data'));
    var index = 0;
    for (var i = 0; i < project_file_list.length; i++) {
        var file_list = project_file_list[i].error_list;
        console.log(file_list);
        var provider_tr = '<tr><td colspan="4">' + project_file_list[i].provider + '</td></tr>';
        $(provider_tr).appendTo($('#tree_timestamp_error_data'));
        for (var j = 0; j < file_list.length; j++) { 
                     var op_date =  new Date(file_list[j].operator_date)
                     var y = op_date.getFullYear();
                     var m = ('0' + op_date.getMonth() + 1).slice(-2);
                     var d = ('0' + op_date.getDate()).slice(-2);
                     var h = op_date.getHours();
                     if (h > 12 ) { h -= 12;}else if(h == 0) {h = 12;}
                     var amPm = (h > 11) ? "PM" : "AM"; 
                     var H = ('0' + h).slice(-2);
                     var M = ('0' + op_date.getMinutes()).slice(-2);  
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
                                    '<td>' + y + '-' + m + '-' + d  + ' ' + H + ':' + M + ' ' + amPm + '</td>' +
                                    '<td>' + file_list[j].verify_result_title + '</td>' +
                                    '</tr>';
                     console.log(error_tr);
                     $(error_tr).appendTo($('#tree_timestamp_error_data'));
             index++;
        }
     }
});


