'use strict';

var $ = require('jquery');
var ko = require('knockout');
var bootstrap = require('bootstrap');
var bootbox = require('bootbox');
require('js/osfToggleHeight');

var $osf = require('js/osfHelpers');

const logPrefix = '[metadata] ';

var uploadedFiles = null;

function init() {
    var csrftoken = $('[name=csrfmiddlewaretoken]').val()
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
}

function updateRecords(records, callback) {
    $.ajax({
        url: 'erad/records',
        type: 'POST',
        data: JSON.stringify(records),
        contentType: 'application/json; charset=utf-8',
        timeout: 120000,
        success: function (data) {
            if (callback) {
                callback();
            }
        },
        error: function (jqXHR, textStatus, error) {
            var errorMessage = error;
            if (jqXHR.responseJSON != null && ('message' in jqXHR.responseJSON)) {
                errorMessage = jqXHR.responseJSON.message;
            }
            bootbox.alert({
                message: errorMessage,
                backdrop: true
            });
            if (callback) {
                callback();
            }
        }
    });
}

$('#e-rad-files').on('change', function(event) {
    uploadedFiles = event.target.files;
});

$('#e-rad-update').on('click', function() {
    if (!uploadedFiles) {
        return;
    }
    $('#e-rad-update').attr('disabled', true);
    const textPromises = [];
    for (var i = 0; i < uploadedFiles.length; i ++) {
        const file = uploadedFiles[i];
        textPromises.push(file.text());
    }
    Promise.all(textPromises)
        .then(function(texts) {
            console.log(logPrefix, 'Files', texts.map(function(text, textIndex) {
                return {
                    name: uploadedFiles[textIndex].name,
                    textLength: text.length,
                };
            }));
            const records = texts.map(function(text, textIndex) {
                return {
                    name: uploadedFiles[textIndex].name,
                    text: text,
                };
            });
            updateRecords(records, function() {
                $('#e-rad-update').attr('disabled', false);
            });
        })
        .catch(function(error) {
            $('#e-rad-update').attr('disabled', false);
            bootbox.alert({
                message: error,
                backdrop: true
            });
        });
});

init();
