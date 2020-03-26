'use strict';

var $ = require('jquery');
var ko = require('knockout');
var bootbox = require('bootbox');
require('js/osfToggleHeight');

var $osf = require('js/osfHelpers');
var AddonPermissionsTable = require('js/addonPermissions');
var addonSettings = require('./rdmAddonSettings');

var _ = require('js/rdmGettext')._;
var sprintf = require('agh.sprintf').sprintf;

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
            title: sprintf(_("Disallow %s?"),$osf.htmlEscape(addonFullName)),
            message: sprintf(_("Are you sure you want to disallow the %1$s?<br>"),$osf.htmlEscape(addonFullName)) +
                     sprintf(_("This will revoke access to %1$s for all projects using the accounts.<br><br>"),$osf.htmlEscape(addonFullName)) +
                     sprintf(_("Type the following to continue: <strong>%1$s</strong><br><br>"),$osf.htmlEscape(deletionKey)) +
                     "<input id='" + $osf.htmlEscape(id) + "' type='text' class='bootbox-input bootbox-input-text form-control'>",
            buttons: {
                cancel: {
                    label: _('Cancel')
                },
                confirm: {
                    label: _('Disallow'),
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
                        $osf.growl('Verification failed', _('Strings did not match'));
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
