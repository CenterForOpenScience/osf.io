'use strict';

var $ = require('jquery');
var ko = require('knockout');
var bootbox = require('bootbox');
require('js/osfToggleHeight');

var $osf = require('js/osfHelpers');
var AddonPermissionsTable = require('js/addonPermissions');
var addonSettings = require('./rdmAddonSettings');

/***************
* OAuth addons *
****************/

$('.addon-oauth').each(function(index, elem) {
    var viewModel = new addonSettings.OAuthAddonSettingsViewModel(
        $(elem).data('addon-short-name'),
        $(elem).data('addon-name'),
        $(elem).data('institution-id')
    );
    ko.applyBindings(viewModel, elem);
    viewModel.updateAccounts();
});

/***************
* Allow addons *
****************/

$('.is_allowed input').on('change', function() {
    var $input = $(this);
    var institutionId = $input.data('institution-id');
    var addonName = $input.data('addon-short-name');
    var addonFullName = $input.data('addon-full-name');
    var isAllowed = $input.prop('checked') + 0;
    var url = '/addons/allow/' + addonName + '/' + institutionId + '/' + isAllowed;
    $input.prop('disabled', true);
    var update = function($input, url, isAllowed) {
        $.ajax({
            url: url,
            type: 'GET'
        })
        .done(function(data) {
            $input.prop('disabled', false);
        })
        .fail(function(xhr, status, error) {
            $input.prop('checked', !isAllowed);
            $input.prop('disabled', false);
            bootbox.alert({
                message: error,
                backdrop: true
            });
        });
    };
    if (isAllowed) {
        update($input, url, isAllowed);
    } else {
        var deletionKey = Math.random().toString(36).slice(-8);
        var id = addonName + "DeleteKey";
        bootbox.confirm({
            title: "Disallow "+$osf.htmlEscape(addonFullName)+"?",
            message: "Are you sure you want to disallow the "+$osf.htmlEscape(addonFullName)+"?<br>" +
                     "This will revoke access to "+$osf.htmlEscape(addonFullName)+" for all projects using the accounts.<br><br>" + 
                     "Type the following to continue: <strong>" + $osf.htmlEscape(deletionKey) + "</strong><br><br>" +
                     "<input id='" + $osf.htmlEscape(id) + "' type='text' class='bootbox-input bootbox-input-text form-control'>",
            buttons: {
                cancel: {
                    label: 'Cancel'
                },
                confirm: {
                    label: 'Disallow',
                    className: 'btn-danger'
                }
            },
            callback: function (result) {
                if (result) {
                    if ($('#'+id).val() == deletionKey) {
                        update($input, url, isAllowed);
                    } else {
                        $input.prop('checked', !isAllowed);
                        $input.prop('disabled', false);
                        $osf.growl('Verification failed', 'Strings did not match');
                    }
                } else {
                    $input.prop('checked', !isAllowed);
                    $input.prop('disabled', false);
                }
            }
        });
    }
});

/***************
* Force addons *
****************/

$('.is_forced input').on('change', function() {
    var $input = $(this);
    var institutionId = $input.data('institution-id');
    var addonName = $input.data('addon-short-name');
    var isForced = $input.prop('checked') + 0;
    var url = '/addons/force/' + addonName + '/' + institutionId + '/' + isForced;
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
