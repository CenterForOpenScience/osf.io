'use strict';

var $ = require('jquery');
var ko = require('knockout');
var bootbox = require('bootbox');
var Raven = require('raven-js');
require('js/osfToggleHeight');

var $osf = require('js/osfHelpers');
var AddonPermissionsTable = require('js/addonPermissions');
var addonSettings = require('js/addonSettings');

ko.punches.enableAll();


// Show capabilities modal on selecting an addon; unselect if user
// rejects terms
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

var addonEnabledSettings = window.contextVars.addonEnabledSettings;
for (var i=0; i < addonEnabledSettings.length; i++) {
       var addonName = addonEnabledSettings[i];
       if (typeof window.contextVars.addonsWithNodes !== 'undefined' && addonName in window.contextVars.addonsWithNodes) {
           AddonPermissionsTable.init(window.contextVars.addonsWithNodes[addonName].shortName,
                                      window.contextVars.addonsWithNodes[addonName].fullName);
   }
}

$(document).ready(function(){
// Separately load addons whose data is loaded on the backend as opposed to async javascript.
    var makoLoadedAddons = ['dropbox', 'github', 'box', 'figshare', 'googledrive', 's3'];
    makoLoadedAddons.forEach(function(addon){
        $('#'+ addon + '-header').osfToggleHeight({height: 140});
    });
});

/* Before closing the page, Check whether the newly checked addon are updated or not */
$(window).on('beforeunload',function() {
    //new checked items but not updated
    var checked = uncheckedOnLoad.filter('#selectAddonsForm input:checked');
    //new unchecked items but not updated
    var unchecked = checkedOnLoad.filter('#selectAddonsForm input:not(:checked)');

    if(unchecked.length > 0 || checked.length > 0) {
        return 'The changes on addon setting are not submitted!';
    }
});

/***************
* OAuth addons *
****************/

$('.addon-oauth').each(function(index, elem) {
// Applies to Mendeley, Zotero.  There is a separate code for dataverse in DataverseUserConfig.js

    var viewModel = new addonSettings.OAuthAddonSettingsViewModel(
        $(elem).data('addon-short-name'),
        $(elem).data('addon-name')
    );
    ko.applyBindings(viewModel, elem);
    viewModel.updateAccounts();
});

