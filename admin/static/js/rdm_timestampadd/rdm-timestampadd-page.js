'use strict';

var $ = require('jquery');
var jQuery = $;
var Raven = require('raven-js');
var urls = window.timestampaddUrls;


$(function () {
    function getCookie (name) {
        var cookieValue = null;
        if (document.cookie && document.cookie != '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = jQuery.trim(cookies[i]);
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) == (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    var csrftoken = getCookie('admin-csrf');
    function csrfSafeMethod (method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }
    $.ajaxSetup({
        crossDomain: false, // obviates need for sameOrigin test
        beforeSend: function (xhr, settings) {
            if (!csrfSafeMethod(settings.type)) {
                xhr.setRequestHeader('X-CSRFToken', csrftoken);
            }
        }
    });

    var btnVerify_onclick = function () {
        if ($('#btn-verify').attr('disabled') != undefined || $('#btn-addtimestamp').attr('disabled') != undefined) {
            return false;
        }
        $('#btn-verify').attr('disabled', true);
        $('#btn-addtimestamp').attr('disabled', true);
        $('#timestamp_errors_spinner').text('Storage files list gathering ...');
        var postData = {};
        var fileCnt = 0;
        $.ajax({
            url: urls.verify,
            data: postData,
            dataType: 'json',
            method: 'POST'
        }).done(function (data) {
            var projectFileList = data['provider_file_list'];
            var i, j;
            var fileList;
            for (i = 0; i < projectFileList.length; i++) {
                fileList = projectFileList[i].provider_file_list;
                for (j = 0; j < fileList.length; j++) {
                    fileCnt++;
                }
            }
            var successCnt = 0;
            for (i = 0; i < projectFileList.length; i++) {
                fileList = projectFileList[i].provider_file_list;
                for (j = 0; j < fileList.length; j++) {
                    var postData = {'provider': projectFileList[i].provider,
                        'file_id': fileList[j].file_id,
                        'file_path': fileList[j].file_path,
                        'file_name': fileList[j].file_name,
                        'version': fileList[j].version};
                    $.ajax({
                        url: urls.verifyData,
                        data: postData,
                        dataType: 'json',
                        method: 'POST'
                    }).done(function () {
                        successCnt++;
                        $('#timestamp_errors_spinner').text('Verification files : ' + successCnt + ' / ' + fileCnt + ' ...');
                        if (successCnt == fileCnt) {
                            $('#timestamp_errors_spinner').text('Verification (100%) and Refreshing...');
                            window.location.reload();
                        }
                    }).fail(function (xhr, status, error) {
                        $('#btn-verify').removeAttr('disabled');
                        $('#btn-addtimestamp').removeAttr('disabled');
                        $('#timestamp_errors_spinner').text('Error : ' + fileList[j].file_path);
                        Raven.captureMessage('Timestamp Add Error: ' + filePathList[index], {
                            extra: {
                                url: urls.addTimestampData,
                                status: status,
                                error: error
                            }
                        });
                    });
                }
            }
        }).fail(function (xhr, status, error) {
            $('#btn-verify').removeAttr('disabled');
            $('#btn-addtimestamp').removeAttr('disabled');
            $('#timestamp_errors_spinner').text('Error : Storage files list gathering Failed');
            Raven.captureMessage('Timestamp Add Error: ', {
                extra: {
                    url: urls.addTimestampData,
                    status: status,
                    error: error
                }
            });
        });
    };

    var btnAddtimestamp_onclick = function () {
        if ($('#btn-verify').attr('disabled') != undefined || $('#btn-addtimestamp').attr('disabled') != undefined) {
            return false;
        }

        var timestampAdd = $('#timestamp_error_list .addTimestamp').map(function () {
            if ($(this).find('#addTimestampCheck').prop('checked')) {
                return {
                    provider: $(this).find('#provider').val(),
                    file_id: $(this).find('#file_id').val(),
                    file_path: $(this).find('#file_path').val(),
                    project_id: $(this).find('#project_id').val(),
                    version: $(this).find('#version').val(),
                    file_name: $(this).find('#file_name').val(),
                };
            }
            return null;
        });

        $('#btn-verify').attr('disabled', true);
        $('#btn-addtimestamp').attr('disabled', true);
        $('#timestamp_errors_spinner').text('Addtimestamp loading ...');
        var successCnt = 0;

        for (var i = 0; i < timestampAdd.length; i++) {
            var post_data = {
                'provider': timestampAdd[i]['provider'],
                'file_id': timestampAdd[i]['file_id'],
                'file_path': timestampAdd[i]['file_path'],
                'file_name': timestampAdd[i]['file_name'],
                'version': timestampAdd[i]['version']
            };
            $.ajax({
                url: urls.addTimestampData,
                data: post_data,
                dataType: 'json',
                method: 'POST'
            }).done(function () {
                successCnt++;
                $('#timestamp_errors_spinner').text('Adding Timestamp files : ' + successCnt + ' / ' + timestampAdd.length + ' ...');
                if (successCnt ==  timestampAdd.length) {
                    $('#timestamp_errors_spinner').text('Added Timestamp (100%) and Refreshing...');
                    window.location.reload();
                }
            }).fail(function (xhr, status, error) {
                $('#btn-verify').removeAttr('disabled');
                $('#btn-addtimestamp').removeAttr('disabled');
                $('#timestamp_errors_spinner').text('Error : Timestamp Add Failed');
                Raven.captureMessage('Timestamp Add Error: ' + filePathList[index], {
                    extra: {
                        url: urls.addTimestampData,
                        status: status,
                        error: error
                    }
                });
            });
        }
    };

    $('#addTimestampAllCheck').on('change', function () {
        $('input[id=addTimestampCheck]').prop('checked', this.checked);
    });

    var document_onready = function () {
        $('#btn-verify').on('click', btnVerify_onclick).focus();
        $('#btn-addtimestamp').on('click', btnAddtimestamp_onclick).focus();
    };
    $(document).ready(document_onready);
});
