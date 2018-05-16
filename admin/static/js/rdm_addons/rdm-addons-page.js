'use strict';

var $ = require('jquery');
var ko = require('knockout');
var bootstrap = require('bootstrap');
var bootbox = require('bootbox');
require('js/osfToggleHeight');

var $osf = require('js/osfHelpers');
var AddonPermissionsTable = require('js/addonPermissions');
var addonSettings = require('./rdmAddonSettings');

// Show capabilities modal on selecting an addon; unselect if user
// rejects terms
/*
$('.addon-select').on('change', function() {
    var that = this;
    var $that = $(that);
    if ($that.is(':checked')) {
        var name = $that.attr('name');
        var capabilities = $('#capabilities-' + name).html();
        if (capabilities) {
            bootbox.confirm({
                message: capabilities,
                callback: function(result) {
                    if (!result) {
                        $that.attr('checked', false);
                    }
                },
                buttons:{
                    confirm:{
                        label:'Confirm'
                    }
                }
        });
        }
    }
});
*/

/*
var checkedOnLoad = $('#selectAddonsForm input:checked');
var uncheckedOnLoad = $('#selectAddonsForm input:not(:checked)');

// TODO: Refactor into a View Model
$('#selectAddonsForm').on('submit', function() {

    var formData = {};
    $('#selectAddonsForm').find('input').each(function(idx, elm) {
        var $elm = $(elm);
        formData[$elm.attr('name')] = $elm.is(':checked');
    });

    var unchecked = checkedOnLoad.filter('#selectAddonsForm input:not(:checked)');

    var submit = function() {
        var request = $osf.postJSON('/api/v1/settings/addons/', formData);
        request.done(function() {
            checkedOnLoad = $('#selectAddonsForm input:checked');
            uncheckedOnLoad = $('#selectAddonsForm input:not(:checked)');
            window.location.reload();
        });
        request.fail(function() {
            var msg = 'Sorry, we had trouble saving your settings. If this persists please contact <a href="mailto: support@osf.io">support@osf.io</a>';
            bootbox.alert({
                title: 'Request failed',
                message: msg,
                buttons:{
                    ok:{
                        label:'Close',
                        className:'btn-default'
                    }
                }
            });
        });
    };

    if(unchecked.length > 0) {
        var uncheckedText = $.map(unchecked, function(el){
            return ['<li>', $(el).closest('label').text().trim(), '</li>'].join('');
        }).join('');
        uncheckedText = ['<ul>', uncheckedText, '</ul>'].join('');
        bootbox.confirm({
            title: 'Are you sure you want to remove the add-ons you have deselected? ',
            message: uncheckedText,
            callback: function(result) {
                if (result) {
                    submit();
                } else{
                    unchecked.each(function(i, el){ $(el).prop('checked', true); });
                }
            },
            buttons:{
                confirm:{
                    label:'Remove',
                    className:'btn-danger'
                }
            }
        });
    }
    else {
        submit();
    }
    return false;
});
*/

/*
var addonEnabledSettings = window.contextVars.addonEnabledSettings;
for (var i=0; i < addonEnabledSettings.length; i++) {
       var addonName = addonEnabledSettings[i];
       if (typeof window.contextVars.addonsWithNodes !== 'undefined' && addonName in window.contextVars.addonsWithNodes) {
           AddonPermissionsTable.init(window.contextVars.addonsWithNodes[addonName].shortName,
                                      window.contextVars.addonsWithNodes[addonName].fullName);
   }
}
*/

/* Before closing the page, Check whether the newly checked addon are updated or not */
/*
$(window).on('beforeunload',function() {
    //new checked items but not updated
    var checked = uncheckedOnLoad.filter('#selectAddonsForm input:checked');
    //new unchecked items but not updated
    var unchecked = checkedOnLoad.filter('#selectAddonsForm input:not(:checked)');

    if(unchecked.length > 0 || checked.length > 0) {
        return 'The changes on addon setting are not submitted!';
    }
});
*/

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
                    label: 'Delete',
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
