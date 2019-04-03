'use strict';

var $ = require('jquery');
var nodeApiUrl = window.contextVars.node.urls.api;
var timestampCommon = require('./timestamp-common.js');
timestampCommon.setWebOrAdmin('web');


$(document).ready(function () {
    timestampCommon.init();
});

$(function () {
    $('#btn-verify').on('click', function () {
        if ($('#btn-verify').attr('disabled') !== undefined || $('#btn-addtimestamp').attr('disabled') !== undefined) {
            return false;
        }
        timestampCommon.verify({
            urlVerify: 'json/',
            urlVerifyData: nodeApiUrl + 'timestamp/timestamp_error_data/',
            method: 'GET'
        });
    });

    $('#btn-addtimestamp').on('click', function () {
        if ($('#btn-verify').attr('disabled') !== undefined || $('#btn-addtimestamp').attr('disabled') !== undefined) {
            return false;
        }
        timestampCommon.add({
            url: nodeApiUrl + 'timestamp/add_timestamp/',
            method: 'POST'
        });
    });

    $('#btn-cancel').on('click', function () {
        if ($('#btn-cancel').attr('disabled') !== undefined) {
            return false;
        }
        timestampCommon.cancel(nodeApiUrl + 'timestamp/cancel_task/');
    });

    $('#btn-download').on('click', function () {
        timestampCommon.download();
    });

    $('#timestamp_errors_spinner').hide();
});
