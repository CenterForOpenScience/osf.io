'use strict';

var ko = require('knockout');
var $ = require('jquery');
var bootbox = require('bootbox');
var $osf = require('js/osfHelpers');

var nodeApiUrl = window.contextVars.node.urls.api;

var GitLabConfigHelper = (function() {

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

    var createRepo = function() {

        var $elm = $('#addonSettingsGitLab');
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
                    nodeApiUrl + 'gitlab/repo/create/',
                    {name: repoName, user: $("#gitlabUser").val()}
                ).done(function (response) {
                        $select.append('<option value="' + response.repo['id'] + '">' + $osf.htmlEscape(response.repo['path_with_namespace']) + '</option>');
                        $select.val(response.repo['id']);
                        updateHidden($select);
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

        $('#gitlabCreateRepo').on('click', function() {
            createRepo();
        });

        $('#gitlabImportToken').on('click', function() {
            askImport();
        });

        $('#gitlabCreateToken').on('click', function() {
            window.oauthComplete = function(res) {
                askImport();
            };
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

})();

module.exports = GitLabConfigHelper;
