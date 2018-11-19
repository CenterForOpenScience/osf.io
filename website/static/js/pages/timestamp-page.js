'use strict';

var $ = require('jquery');
var nodeApiUrl = window.contextVars.node.urls.api;
var projectFileList = window.contextVars.project_file_list;
var timestampCommon = require('./timestamp-common.js');


$(document).ready(function () {
    var index = 0;
    for (var i = 0; i < projectFileList.length; i++) {
        var fileList = projectFileList[i].error_list;
        var providerTr = '<tr><td colspan="5"><b>' + projectFileList[i].provider + '</b></td></tr>';
        $(providerTr).appendTo($('#timestamp_error_list'));
        for (var j = 0; j < fileList.length; j++) {
            var errorTr =
                '<tr class="addTimestamp">' +
                '<td>' +
                '<input type="checkBox" id="addTimestampCheck" style="width: 15px; height: 15px;" value="' + index + '"/>' +
                '<td>' + fileList[j].file_path + '</td>' +
                '<input type="hidden" id="provider" value="' + projectFileList[i].provider + '" />' +
                '<input type="hidden" id="file_id" value="' + fileList[j].file_id + '" />' +
                '<input type="hidden" id="file_path" value="' + fileList[j].file_path + '" />' +
                '<input type="hidden" id="version" value="' + fileList[j].version + '" />' +
                '<input type="hidden" id="file_name" value="' + fileList[j].file_name + '" />' +
                '</td>' +
                '<td>' + fileList[j].operator_user + '</td>' +
                '<td>' + fileList[j].operator_date + '</td>' +
                '<td>' + fileList[j].verify_result_title + '</td>' +
                '</tr>';
            $(errorTr).appendTo($('#timestamp_error_list'));
            index++;
        }
    }
});

$(function () {
    var btnVerify_onclick = function () {
        if ($('#btn-verify').attr('disabled') != undefined || $('#btn-addtimestamp').attr('disabled') != undefined) {
            return false;
        }
        timestampCommon.verify({
            urlVerify: 'json/',
            urlVerifyData: nodeApiUrl + 'timestamp/timestamp_error_data/',
            method: 'GET'
        });
    };

    var btnAddtimestamp_onclick = function () {
        if ($('#btn-verify').attr('disabled') != undefined || $('#btn-addtimestamp').attr('disabled') != undefined) {
            return false;
        }
        timestampCommon.add({
            url: nodeApiUrl + 'timestamp/add_timestamp/',
            method: 'GET'
        });
    };

    $('#addTimestampAllCheck').on('change', function () {
        $('input[id=addTimestampCheck]').prop('checked', this.checked);
    });

    var document_onready = function () {
        $('#btn-verify').on('click', btnVerify_onclick);
        $('#btn-addtimestamp').on('click', btnAddtimestamp_onclick).focus();
    };

    $(document).ready(document_onready);
    $('#timestamp_errors_spinner').hide();
});
