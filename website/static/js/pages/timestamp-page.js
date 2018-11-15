'use strict';

var $ = require('jquery');
var $osf = require('js/osfHelpers');
var node = window.contextVars.node;

var nodeApiUrl = window.contextVars.node.urls.api;
var projectFileList = window.contextVars.project_file_list;


$(document).ready(function () {
    var index = 0;
    for (var i = 0; i < projectFileList.length; i++) {
        var fileList = projectFileList[i].error_list;
        var providerTr = '<tr><td colspan="5"><b>' + projectFileList[i].provider + '</b></td></tr>';
        $(providerTr).appendTo($('#tree_timestamp_error_data'));
        for (var j = 0; j < fileList.length; j++) {
            var errorTr =
                '<tr>' +
                '<td class="addTimestamp">' +
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
            $(errorTr).appendTo($('#tree_timestamp_error_data'));
            index++;
        }
     }
});

$(function () {
    var btnVerify_onclick = function (event) {
        if($("#btn-verify").attr("disabled") != undefined || $("#btn-addtimestamp").attr("disabled") != undefined) {
            return false;
        }

        $("#btn-verify").attr("disabled", true);
        $("#btn-addtimestamp").attr("disabled", true);
        $("#timestamp_errors_spinner").text("Storage files list gathering ...");
        var postData = {}
        var fileCnt = 0;
        $.ajax({
            beforeSend: function () {
                $("#timestamp_errors_spinner").show();
            },
            url: 'json/',
            data: postData,
            dataType: 'json'
        }).done(function(projectFileList) {
            projectFileList = projectFileList.provider_list;
            for (var i = 0; i < projectFileList.length; i++) {
                var fileList = projectFileList[i].provider_file_list;
                for (var j = 0; j < fileList.length; j++) {
                    fileCnt++;
                }
            }
            var index = 0;
            var successCnt = 0;
            for (var i = 0; i < projectFileList.length; i++) {
                var provider_tr = '<tr><td colspan="4">' + projectFileList[i].provider + '</td></tr>';
                var fileList = projectFileList[i].provider_file_list;
                var provider_output_flg = false;
                for (var j = 0; j < fileList.length; j++) {
                    var postData = {'provider': projectFileList[i].provider,
                        'file_id': fileList[j].file_id,
                        'file_path': fileList[j].file_path,
                        'file_name': fileList[j].file_name,
                        'version': fileList[j].version};
                    $.ajax({
                        url:  nodeApiUrl + 'timestamp/timestamp_error_data/',
                        data: postData,
                        dataType: 'json'
                    }).done(function(data) {
                        successCnt++;
                        $("#timestamp_errors_spinner").text("Verification files : " + successCnt + " / " + fileCnt + " ...");
                        if (successCnt == fileCnt) {
                            $("#timestamp_errors_spinner").text("Verification (100%) and Refreshing...");
                            window.location.reload();
                        }
                    }).fail(function(xhr, status, error) {
                        $("#btn-verify").removeAttr("disabled");
                        $("#btn-addtimestamp").removeAttr("disabled");
                        $("#timestamp_errors_spinner").text("Error : " + fileList[j].file_path);
                        Raven.captureMessage('Timestamp Add Error: ' + filePathList[index], {
                            extra: {
                                url: url,
                                status: status,
                                error: error
                            }
                        });
                    });
                }
            }
        }).fail(function(xhr, textStatus, error) {
            $("#btn-verify").removeAttr("disabled");
            $("#btn-addtimestamp").removeAttr("disabled");
            $("#timestamp_errors_spinner").text("Error : Storage files list gathering Failed");
            Raven.captureMessage('Timestamp Add Error', {
                extra: {
                    url: url,
                    textStatus: textStatus,
                    error: error
                }
            });
        });
    };

    var btnAddtimestamp_onclick = function(event) {
        if ($("#btn-verify").attr("disabled") != undefined || $("#btn-addtimestamp").attr("disabled") != undefined) {
            return false;
        }

        var inputCheckBoxs = $('[id=addTimestampCheck]:checked').map(function (index, el) {
            return $(this).val();
        });

        if (inputCheckBoxs.length == 0) {
            return false;
        }

        var providerList = $('[id=provider]').map(function (index, el) {
            return $(this).val();
        });

        var fileIdList = $('[id="file_id"]').map(function (index, el) {
            return $(this).val();
        });

        var filePathList = $('[id=file_path]').map(function (index, el) {
            return $(this).val();
        });

        var versionList = $('[id=version]').map(function (index, el) {
            return $(this).val();
        });

        var fileNameList = $('[id=file_name]').map(function (index, el) {
            return $(this).val();
        });

        $("#btn-verify").attr("disabled", true);
        $("#btn-addtimestamp").attr("disabled", true);
        $("#timestamp_errors_spinner").text("Addtimestamp loading ...");
        var errorFlg = false;
        var successCnt = 0;
        var index;
        for (var i = 0; i < inputCheckBoxs.length; i++) {
            index = inputCheckBoxs[i];
            var postData = {'provider': providerList[index],
                'file_id': fileIdList[index],
                'file_path': filePathList[index],
                'file_name': fileNameList[index],
                'version': versionList[index]};
            $.ajax({
                beforeSend: function(){
                    $("#timestamp_errors_spinner").show();
                },
                url: nodeApiUrl + 'timestamp/add_timestamp/',
                data: postData,
                dataType: 'json'
            }).done(function(data) {
                successCnt++;
                $("#timestamp_errors_spinner").text("Adding Timestamp files : " + successCnt + " / " + inputCheckBoxs.length + " ...");
                if (successCnt ==  inputCheckBoxs.length) {
                    $("#timestamp_errors_spinner").text("Added Timestamp (100%) and Refreshing...");
                    window.location.reload();
                }
            }).fail(function(xhr, textStatus, error) {
                $("#btn-verify").removeAttr("disabled");
                $("#btn-addtimestamp").removeAttr("disabled");
                $("#timestamp_errors_spinner").text("Error : Timestamp Add Failed");
                Raven.captureMessage('Timestamp Add Error: ' + filePathList[index], {
                    extra: {
                        url: url,
                        textStatus: textStatus,
                        error: error
                    }
                });
            });
        }
    };

    $('#addTimestampAllCheck').on('change', function() {
        $('input[id=addTimestampCheck]').prop('checked', this.checked);
    });

    var document_onready = function (event) {
        $("#btn-verify").on("click", btnVerify_onclick);
        $("#btn-addtimestamp").on("click", btnAddtimestamp_onclick).focus();
    };

    $(document).ready(document_onready);
    $("#timestamp_errors_spinner").hide();
});
