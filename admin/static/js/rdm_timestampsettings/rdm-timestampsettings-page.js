'use strict';

var $ = require('jquery');
var ko = require('knockout');
var bootstrap = require('bootstrap');
var bootbox = require('bootbox');
require('js/osfToggleHeight');

var $osf = require('js/osfHelpers');

/**************************************
* Force institution timestamp pattern *
***************************************/
$('.is_forced input').on('change', function() {
    var $input = $(this);
    var institutionId = $input.data('institution-id');
    var institutionName = $input.data('institution-short-name');
    var isForced = $input.prop('checked') + 0;
    var timestampAddPattern = $("#timestamp_pattern_" + institutionId).val();
    var url = '/timestampsettings/force/' + institutionId + '/' + timestampAddPattern + '/' + isForced;
    $input.prop('disabled', true);
    $.ajax({
        url: url,
        type: 'GET'
    })
    .done(function(data) {
        $input.prop('disabled', false);
    })
    .fail(function(xhr, status, error) {
        $input.prop('checked', !isForced);
        $input.prop('disabled', false);
        bootbox.alert({
            message: error,
            backdrop: true
        });
    });
});

/**************************************
* Change node timestamp pattern       *
***************************************/
$('.is_changed input').on('click', function() {
    var $input = $(this);
    var institutionId = $input.data('institution-id');
    var nodeGuid = $input.data('node-guid');
    var timestampAddPattern = $("#" + nodeGuid).val();
    var url = '/timestampsettings/' + institutionId +'/nodes/change/' + nodeGuid + '/' + timestampAddPattern;
    console.log('url:' + url);
    $input.prop('disabled', true);
    $.ajax({
        url: url,
        type: 'GET'
    })
    .done(function(data) {
        $input.prop('disabled', false);
    })
    .fail(function(xhr, status, error) {
        $input.prop('disabled', false);
        bootbox.alert({
            message: error,
            backdrop: true
        });
    });
});

