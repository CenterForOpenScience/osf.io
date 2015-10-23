webpackJsonp([32],{

/***/ 0:
/***/ function(module, exports, __webpack_require__) {

'use strict';

var $ = __webpack_require__(38);
var ko = __webpack_require__(48);
var bootbox = __webpack_require__(138);
var Raven = __webpack_require__(52);
__webpack_require__(195);

var $osf = __webpack_require__(47);
var AddonPermissionsTable = __webpack_require__(384);
var addonSettings = __webpack_require__(196);

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
    $('.addon-auth-table').osfToggleHeight({height: 140});
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
    var viewModel = new addonSettings.OAuthAddonSettingsViewModel(
        $(elem).data('addon-short-name'),
        $(elem).data('addon-name')
    );
    ko.applyBindings(viewModel, elem);
    viewModel.updateAccounts();
});



/***/ },

/***/ 196:
/***/ function(module, exports, __webpack_require__) {

'use strict';

var $ = __webpack_require__(38);
var ko = __webpack_require__(48);
var bootbox = __webpack_require__(138);
var Raven = __webpack_require__(52);
var oop = __webpack_require__(146);

var ConnectedProject = function(data) {
    var self = this;
    self.title = data.title;
    self.id = data.id;
    self.urls = data.urls;
};

var ExternalAccount = oop.defclass({
    constructor: function(data) {
        var self = this;
        self.name = data.display_name;
        self.id = data.id;
        self.profileUrl = data.profile_url;
        self.providerName = data.provider_name;

        self.connectedNodes = ko.observableArray();

        ko.utils.arrayMap(data.nodes, function(item) {
            self.connectedNodes.push(new ConnectedProject(item));
        });
    },
    _deauthorizeNodeConfirm: function(node) {
        var self = this;
        var url = node.urls.deauthorize;
        var request = $.ajax({
                url: url,
                type: 'DELETE'
            })
            .done(function(data) {
                self.connectedNodes.remove(node);
            })
            .fail(function(xhr, status, error) {
                Raven.captureMessage('Error deauthorizing node: ' + node.id, {
                    url: url,
                    status: status,
                    error: error
                });
            });
    },
    deauthorizeNode: function(node) {
        var self = this;
        bootbox.confirm({
            title: 'Remove addon?',
            message: 'Are you sure you want to remove the ' + self.providerName + ' authorization from this project?',
            callback: function(confirm) {
                if (confirm) {
                    self._deauthorizeNodeConfirm(node);
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
});

var OAuthAddonSettingsViewModel = oop.defclass({
    constructor: function(name, displayName) {
        var self = this;
        self.name = name;
        self.properName = displayName;
        self.accounts = ko.observableArray();
        self.message = ko.observable('');
        self.messageClass = ko.observable('');
    },
    setMessage: function(msg, cls) {
        var self = this;
        self.message(msg);
        self.messageClass(cls || 'text-info');
    },
    connectAccount: function() {
        var self = this;
        window.oauthComplete = function() {
            self.setMessage('');
            var accountCount = self.accounts().length;
            self.updateAccounts().done( function() {
                (self.accounts().length > accountCount) ?
                    self.setMessage('Add-on successfully authorized. To link this add-on to an OSF project, go to the settings page of the project, enable ' + self.properName + ', and choose content to connect.', 'text-success') :
                    self.setMessage('Error while authorizing addon. Please log in to your ' + self.properName + ' account and grant access to the OSF to enable this addon.', 'text-failure');
                });
        };
        window.open('/oauth/connect/' + self.name + '/');
    },
    askDisconnect: function(account) {
        var self = this;
        bootbox.confirm({
            title: 'Disconnect Account?',
            message: '<p class="overflow">' +
                'Are you sure you want to disconnect the ' + self.properName + ' account <strong>' +
                account.name + '</strong>? This will revoke access to ' + self.properName + ' for all projects you have authorized.' +
                '</p>',
            callback: function(confirm) {
                if (confirm) {
                    self.disconnectAccount(account);
                    self.setMessage('');
                }
            },
            buttons:{
                confirm:{
                    label:'Delete',
                    className:'btn-danger'
                }
            }
        });
    },
    disconnectAccount: function(account) {
        var self = this;
        var url = '/api/v1/oauth/accounts/' + account.id + '/';
        var request = $.ajax({
            url: url,
            type: 'DELETE'
        });
        request.done(function(data) {
            self.updateAccounts();
        });
        request.fail(function(xhr, status, error) {
            Raven.captureMessage('Error while removing addon authorization for ' + account.id, {
                url: url,
                status: status,
                error: error
            });
        });
        return request;
    },
    updateAccounts: function() {
        var self = this;
        var url = '/api/v1/settings/' + self.name + '/accounts/';
        var request = $.get(url);
        request.done(function(data) {
            self.accounts($.map(data.accounts, function(account) {
                return new ExternalAccount(account);
            }));
        });
        request.fail(function(xhr, status, error) {
            Raven.captureMessage('Error while updating addon account', {
                url: url,
                status: status,
                error: error
            });
        });
        return request;
    }
});

module.exports = {
    ConnectedProject: ConnectedProject,
    ExternalAccount: ExternalAccount,
    OAuthAddonSettingsViewModel: OAuthAddonSettingsViewModel
};


/***/ },

/***/ 384:
/***/ function(module, exports, __webpack_require__) {

/**
 * Module for listing all projects/components authorized for a given addon
 * on the user settings page. Also handles revoking addon access from these
 * projects/components.
 */
'use strict';

var $ = __webpack_require__(38);
var bootbox = __webpack_require__(138);

var $osf = __webpack_require__(47);

var AddonPermissionsTable = {
    init: function(addonShortName, addonFullname) {
        $('.' + addonShortName + '-remove-token').on('click', function (event) {
            var nodeId = $(this).attr('node-id');
            var apiUrl = $(this).attr('api-url')+ addonShortName + '/config/';
            bootbox.confirm({
                title: 'Remove addon?',
                message: 'Are you sure you want to disconnnect the ' + addonFullname + ' account from this project?',
                callback: function (confirm) {
                    if (confirm) {
                        $.ajax({
                            type: 'DELETE',
                            url: apiUrl,

                            success: function (response) {

                                $('#' + addonShortName + '-' + nodeId + '-auth-row').hide();
                                var numNodes = $('#' + addonShortName + '-auth-table tr:visible').length;
                                if (numNodes === 1) {
                                    $('#' + addonShortName + '-auth-table').hide();
                                }
                                if (numNodes === 4) {
                                    $('#' + addonShortName + '-more').hide();
                                    $('#' + addonShortName+ '-less').hide();
                                }
                            },

                            error: function () {
                                $osf.growl('An error occurred, the account is still connected to the project. ',
                                    'If the issue persists, please report it to <a href="mailto:support@osf.io">support@osf.io</a>.');
                            }
                        });
                    }
                },
                buttons:{
                    confirm:{
                        label:'Remove',
                        className:'btn-danger'
                    }
                }
            });
        });
    }
};

module.exports = AddonPermissionsTable;


/***/ }

});
//# sourceMappingURL=profile-settings-addons-page.js.map