'use strict';

var ko = require('knockout');
var $ = require('jquery');
var bootbox = require('bootbox');
var $osf = require('js/osfHelpers');

var nodeApiUrl = window.contextVars.node.urls.api;

var GithubConfigHelper = (function() {

    var connectExistingAccount = function(accountId) {
        $osf.putJSON(
                nodeApiUrl + 'github/user_auth/',
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
        $('#githubUser').val($.trim(repoParts[0]));
        $('#githubRepo').val($.trim(repoParts[1]));
    };

    var displayError = function(msg) {
        $('#addonSettingsGithub').find('.addon-settings-message')
            .text('Error: ' + msg)
            .removeClass('text-success').addClass('text-danger')
            .fadeOut(100).fadeIn();
    };

    var createRepo = function() {

        var $elm = $('#addonSettingsGithub');
        var $select = $elm.find('select');

        bootbox.prompt({
            title: 'Name your new repo',
            placeholder: 'Repo name',
            callback: function (repoName) {
                // Return if cancelled
                if (repoName === null) {
                    return;
                }

                if (repoName === '') {
                    displayError('Your repo must have a name');
                    return;
                }

                $osf.postJSON(
                    nodeApiUrl + 'github/repo/create/',
                    {name: repoName}
                ).done(function (response) {
                        var repoName = response.user + ' / ' + response.repo;
                        $select.append('<option value="' + repoName + '">' + $osf.htmlEscape(repoName) + '</option>');
                        $select.val(repoName);
                        updateHidden(repoName);
                    }).fail(function () {
                        displayError('Could not create repository');
                    });
            },
            buttons:{
                confirm:{
                    label: 'Save',
                    className:'btn-success'
                }
            }
        });
    };

    var askImport = function() {
        $.get('/api/v1/settings/github/accounts/'
        ).done(function(data){
            var accounts = data.accounts.map(function(account) {
                return {
                    name: account.display_name,
                    id: account.id
                };
            });
            if (accounts.length > 1) {
                bootbox.prompt({
                    title: 'Choose GitHub Account to Import',
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
                    title: 'Import GitHub Account?',
                    message: 'Are you sure you want to link your GitHub account with this project?',
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
            displayError('Could not GET GitHub accounts for user.');
        });
    };

    $(document).ready(function() {
        $('#githubSelectRepo').on('change', function() {
            var value = $(this).val();
            if (value) {
                updateHidden(value);
            }
        });

        $('#githubCreateRepo').on('click', function() {
            createRepo();
        });

        $('#githubImportToken').on('click', function() {
            askImport();
        });

        $('#githubCreateToken').on('click', function() {
            window.oauthComplete = function(res) {
                askImport();
            };
            window.open('/oauth/connect/github/');
        });

        $('#githubRemoveToken').on('click', function() {
            bootbox.confirm({
                title: 'Disconnect GitHub Account?',
                message: 'Are you sure you want to remove this GitHub account?',
                callback: function(confirm) {
                    if(confirm) {
                        $.ajax({
                        type: 'DELETE',
                        url: nodeApiUrl + 'github/user_auth/'
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

        $('#addonSettingsGithub .addon-settings-submit').on('click', function() {
            if (!$('#githubRepo').val()) {
                return false;
            }
        });

    });

})();

module.exports = GithubConfigHelper;
