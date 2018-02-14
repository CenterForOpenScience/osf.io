var ko = require('knockout');
var $ = require('jquery');
var bootbox = require('bootbox');
var $osf = require('js/osfHelpers');
var oop = require('js/oop');
var UserViewModel = require('./gitlabUserConfig.js').GitLabViewModel;

var nodeApiUrl = window.contextVars.node.urls.api;

var connectExistingAccount = function(accountId) {
    $osf.putJSON(
            nodeApiUrl + 'gitlab/user_auth/',
            {'external_account_id': accountId}
        ).done(function() {
                if($osf.isIE()){
                    window.location.hash = '#configureAddonsAnchor';
                }
                window.location.reload();
        }).fail(
            $osf.handleJSONError
        );
};

var updateHidden = function(element) {
    var repoParts = $("option:selected", element).text().split('/');

    $('#gitlabUser').val($.trim(repoParts[0]));
    $('#gitlabRepo').val($.trim(repoParts[1]));
    $('#gitlabRepoId').val(element.val());
};

var displayError = function(msg) {
    $('#addonSettingsGitLab').find('.addon-settings-message')
        .text('Error: ' + msg)
        .removeClass('text-success').addClass('text-danger')
        .fadeOut(100).fadeIn();
};


var askImport = function() {
    $.get('/api/v1/settings/gitlab/accounts/'
    ).done(function(data){
        var accounts = data.accounts.map(function(account) {
            return {
                name: account.display_name,
                id: account.id
            };
        });
        if (accounts.length > 1) {
            bootbox.prompt({
                title: 'Choose GitLab Account to Import',
                inputType: 'select',
                inputOptions: ko.utils.arrayMap(
                    accounts,
                    function(item) {
                        return {
                            text: $osf.htmlEscape(item.name),
                            value: item.id
                        };
                    }
                ),
                value: accounts[0].id,
                callback: function(accountId) {
                    connectExistingAccount(accountId);
                },
                buttons: {
                    confirm:{
                        label:'Import',
                    }
                }
            });
        } else {
            bootbox.confirm({
                title: 'Import GitLab Account?',
                message: 'Are you sure you want to link your GitLab account with this project?',
                callback: function(confirmed) {
                    if (confirmed) {
                        connectExistingAccount(accounts[0].id);
                    }
                },
                buttons: {
                    confirm: {
                        label:'Import',
                    }
                }
            });
        }
    }).fail(function(xhr, textStatus, error) {
        displayError('Could not GET GitLab accounts for user.');
    });
};

$(document).ready(function() {
    $('#gitlabSelectRepo').on('change', function() {
        var el = $(this);
        if (el.val()) {
            updateHidden(el);
        }
    });

    $('#gitlabImportToken').on('click', function() {
        askImport();
    });

    $('#gitlabRemoveToken').on('click', function() {
        bootbox.confirm({
            title: 'Disconnect GitLab Account?',
            message: 'Are you sure you want to remove this GitLab account?',
            callback: function(confirm) {
                if(confirm) {
                    $.ajax({
                    type: 'DELETE',
                    url: nodeApiUrl + 'gitlab/user_auth/'
                }).done(function() {
                    window.location.reload();
                }).fail(
                    $osf.handleJSONError
                );
                }
            },
            buttons:{
                confirm:{
                    label: 'Disconnect',
                    className: 'btn-danger'
                }
            }
        });
    });

    $('#addonSettingsGitLab .addon-settings-submit').on('click', function() {
        if (!$('#gitlabRepo').val()) {
            return false;
        }
    });

});

var ViewModel = oop.extend(UserViewModel,{
    constructor: function(url){
        var self = this;
        self.name = 'gitlab';
        self.properName = 'GitLab';
        self.accounts = ko.observableArray();
        self.message = ko.observable('');
        self.messageClass = ko.observable('');
        const otherString = 'Other (Please Specify)';

        self.url = url;
        self.properName = 'GitLab';
        self.apiToken = ko.observable();
        self.urls = ko.observable({});
        self.hosts = ko.observableArray([]);
        self.selectedHost = ko.observable();    // Host specified in select element
        self.customHost = ko.observable();      // Host specified in input element
        // Whether the initial data has been loaded
        self.loaded = ko.observable(false);

        // Designated host, specified from select or input element
        self.host = ko.pureComputed(function() {
            return self.useCustomHost() ? self.customHost() : self.selectedHost();
        });
        // Hosts visible in select element. Includes presets and "Other" option
        self.visibleHosts = ko.pureComputed(function() {
            return self.hosts().concat([otherString]);
        });
        // Whether to use select element or input element for host designation
        self.useCustomHost = ko.pureComputed(function() {
            return self.selectedHost() === otherString;
        });
        self.showApiTokenInput = ko.pureComputed(function() {
            return Boolean(self.selectedHost());
        });
        self.tokenUrl = ko.pureComputed(function() {
            return self.host() ? 'https://' + self.host() + '/profile/personal_access_tokens' : null;
        });
    },
    authSuccessCallback: function() {
        askImport();
    }

});

module.exports = {
    GitLabViewModel: ViewModel
};
