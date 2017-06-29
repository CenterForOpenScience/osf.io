'use strict';

var ko = require('knockout');
var $ = require('jquery');
var bootbox = require('bootbox');
var $osf = require('js/osfHelpers');

var nodeApiUrl = window.contextVars.node.urls.api;

var BitbucketConfigHelper = (function() {

    var connectExistingAccount = function(accountId) {
        $osf.putJSON(
                nodeApiUrl + 'bitbucket/user_auth/',
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

    var updateHidden = function(val) {
        var repoParts = val.split('/');
        $('#bitbucketUser').val($.trim(repoParts[0]));
        $('#bitbucketRepo').val($.trim(repoParts[1]));
    };

    var displayError = function(msg) {
        $('#addonSettingsBitbucket').find('.addon-settings-message')
            .text('Error: ' + msg)
            .removeClass('text-success').addClass('text-danger')
            .fadeOut(100).fadeIn();
    };

    var askImport = function() {
        $.get('/api/v1/settings/bitbucket/accounts/'
        ).done(function(data){
            var accounts = data.accounts.map(function(account) {
                return {
                    name: account.display_name,
                    id: account.id
                };
            });
            if (accounts.length > 1) {
                bootbox.prompt({
                    title: 'Choose Bitbucket Account to Import',
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
                    title: 'Import Bitbucket Account?',
                    message: 'Are you sure you want to link your Bitbucket account with this project?',
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
            displayError('Could not GET Bitbucket accounts for user.');
        });
    };

    $(document).ready(function() {
        $('#bitbucketSelectRepo').on('change', function() {
            var value = $(this).val();
            if (value) {
                updateHidden(value);
            }
        });

        $('#bitbucketImportToken').on('click', function() {
            askImport();
        });

        $('#bitbucketCreateToken').on('click', function() {
            window.oauthComplete = function(res) {
                askImport();
            };
            window.open('/oauth/connect/bitbucket/');
        });

        $('#bitbucketRemoveToken').on('click', function() {
            bootbox.confirm({
                title: 'Disconnect Bitbucket Account?',
                message: 'Are you sure you want to remove this Bitbucket account?',
                callback: function(confirm) {
                    if(confirm) {
                        $.ajax({
                        type: 'DELETE',
                        url: nodeApiUrl + 'bitbucket/user_auth/'
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

        $('#addonSettingsBitbucket .addon-settings-submit').on('click', function() {
            if (!$('#bitbucketRepo').val()) {
                return false;
            }
        });

    });

})();

module.exports = BitbucketConfigHelper;
