/**
* Module that controls the S3 user settings. Includes Knockout view-model
* for syncing data.
*/

var ko = require('knockout');
var $ = require('jquery');
var Raven = require('raven-js');
var bootbox = require('bootbox');
require('js/osfToggleHeight');

var language = require('js/osfLanguage').Addons.s3;
var osfHelpers = require('js/osfHelpers');
var addonSettings = require('js/addonSettings');
var ChangeMessageMixin = require('js/changeMessage');


var ExternalAccount = addonSettings.ExternalAccount;

var $modal = $('#s3InputCredentials');


function ViewModel(url) {
    var self = this;

    self.properName = 'Amazon S3';
    self.accessKey = ko.observable();
    self.secretKey = ko.observable();
    self.host = ko.observable();
    self.port = ko.observable();
    self.nickname = ko.observable();
    self.encrypted = ko.observable(true);
    self.account_url = '/api/v1/settings/s3/accounts/';
    self.accounts = ko.observableArray();

    ChangeMessageMixin.call(self);

    /** Reset all fields from S3 credentials input modal */
    self.clearModal = function() {
        self.message('');
        self.messageClass('text-info');
        self.accessKey(null);
        self.secretKey(null);
    };
    /** Send POST request to authorize S3 */
    self.connectAccount = function() {
        // Selection should not be empty
        if (!self.host) {
            self.changeMessage('A host name is required to connect an s3 provider.', 'text-danger');
            return;
        }
        if (!self.port) {
            self.changeMessage('A host name is required to connect an s3 provider.', 'text-danger');
            return;
        }
        if (!self.accessKey() && !self.secretKey()) {
            self.changeMessage('Please enter both an API access key and secret key.', 'text-danger');
            return;
        }

        if (!self.accessKey()) {
            self.changeMessage('Please enter an API access key.', 'text-danger');
            return;
        }

        if (!self.secretKey()) {
            self.changeMessage('Please enter an API secret key.', 'text-danger');
            return;
        }
        return osfHelpers.postJSON(
            self.account_url,
            ko.toJS({
                host: self.host,
                port: self.port,
                encrypted: self.encrypted(),
                access_key: self.accessKey,
                secret_key: self.secretKey,
                nickname: self.nickname
            })
        ).done(function() {
            self.clearModal();
            $modal.modal('hide');
            self.updateAccounts();

        }).fail(function(xhr, textStatus, error) {
            var errorMessage = (xhr.status === 400 && xhr.responseJSON.message !== undefined) ? xhr.responseJSON.message : language.authError;
            self.changeMessage(errorMessage, 'text-danger');
            Raven.captureMessage('Could not authenticate with S3', {
                extra: {
                    url: self.account_url,
                    textStatus: textStatus,
                    error: error
                }
            });
        });
    };

    self.updateAccounts = function() {
        return $.ajax({
            url: url,
            type: 'GET',
            dataType: 'json'
        }).done(function (data) {
            self.accounts($.map(data.accounts, function(account) {
                var externalAccount =  new ExternalAccount(account);
                externalAccount.accessKey = account.oauth_key;
                externalAccount.secretKey = account.oauth_secret;
                return externalAccount;
            }));
            $('#s3-header').osfToggleHeight({height: 160});
        }).fail(function(xhr, status, error) {
            self.changeMessage(language.userSettingsError, 'text-danger');
            Raven.captureMessage('Error while updating addon account', {
                extra: {
                    url: url,
                    status: status,
                    error: error
                }
            });
        });
    };

    self.askDisconnect = function(account) {
        var self = this;
        bootbox.confirm({
            title: 'Disconnect Amazon S3 Account?',
            message: '<p class="overflow">' +
                'Are you sure you want to disconnect the S3 account <strong>' +
                osfHelpers.htmlEscape(account.name) + '</strong>? This will revoke access to S3 for all projects associated with this account.' +
                '</p>',
            callback: function (confirm) {
                if (confirm) {
                    self.disconnectAccount(account);
                }
            },
            buttons:{
                confirm:{
                    label:'Disconnect',
                    className:'btn-danger'
                }
            }
        });
    };

    self.askModify = function(account) {

        var nickname = account.nickname;
        var host = account.host;
        var port = account.port;
        var access_key = '';
        var secret_key = '';
        var encrypted = account.encrypted;
        var modify_modal = document.createElement('div')

        modify_modal.className = 'modal fade in';
        modify_modal.id = 'modify_modal';
        modify_modal.style.display = 'block';
        modify_modal.style.backgroundColor = 'rgba(0,0,0,0.5)';
        document.body.appendChild(modify_modal);
        modify_modal.innerHTML =
            '<div class="modal-dialog modal-lg">' +
                '<div class="modal-content">' +
                    '<div class="modal-header">' +
                        '<h3>Modify Account</h3>' +
                    '</div>' +
                    '<div class="modal-body">' +
                        '<div class="row">' +
                            '<div class="col-sm-3"></div>' +

                            '<div class="col-sm-6">' +
                                '<div class="description">Leave the</div>' +
                                '<div class="form-group nickname">' +
                                    '<label for="s3Addon">Nickname</label>' +
                                    '<input class="form-control" id="_nickname" name="_nickname" data-lpignore=true autocomplete=off />' +
                                '</div>' +
                                '<div class="form-group host">' +
                                    '<label for="s3Addon">Host</label>' +
                                    '<input class="form-control" id="_host" name="_host" data-lpignore=true autocomplete=off />' +
                                '</div>' +

                                '<div class="form-group port">' +
                                    '<label for="s3Addon">Port</label>' +
                                    '<input class="form-control" id="_port" name="_port" data-lpignore=true autocomplete=off />' +
                                '</div>' +

                                '<div class="form-group access_key">' +
                                    '<label for="s3Addon">Access Key</label>' +
                                    '<input class="form-control" id="access_key" name="access_key" data-lpignore=true autocomplete=off />' +
                                '</div>' +
                                '<div class="form-group secret_key">' +
                                    '<label for="s3Addon">Secret Key</label>' +
                                    '<input type="password" class="form-control" id="secret_key" name="secret_key" data-lpignore=true autocomplete=off />' +
                                '</div>' +
                                '<div class="form-group encrypted">' +
                                    '<label class="form-check-label" for="encrypted">' +
                                        'Use TLS Encryption<br>' +
                                        '<input class="form-check-input" type="checkbox" id="encrypted" name="encrypted" data-lpignore=true autocomplete=off />' +
                                    '</label>' +
                                '</div>' +
                            '</div>' +
                        '</div>' +
                    '</div>' +
                    '<div class="modal-footer">' +
                        '<button class="btn btn-default cancel">' +
                            'Cancel' +
                        '</button>' +
                        '<button class="btn btn-warning modify">' +
                            'Modify' +
                        '</button>' +
                    '</div>' +
                '</div>' +
            '</div>';


        var nickname_input = modify_modal.querySelector('.form-group.nickname input');
        nickname_input.addEventListener('input', function(ev) {
            nickname = ev.target.value;
            ev.preventDefault();
            ev.stopImmediatePropagation();
            console.log('hi');
            return false;
        });
        nickname_input.value = nickname;

        var host_input = modify_modal.querySelector('.form-group.host input');
        host_input.addEventListener('input', function(ev) {
            host = ev.target.value;
            ev.preventDefault();
            ev.stopImmediatePropagation();
            return false;
        });
        host_input.value = host;

        var port_input = modify_modal.querySelector('.form-group.port input');
        port_input.addEventListener('input', function(ev) {
            port = ev.target.value;
            ev.preventDefault();
            ev.stopImmediatePropagation();
            return false;
        });
        port_input.value = port;

        var secret_key_input = modify_modal.querySelector('.form-group.secret_key input');
        secret_key_input.addEventListener('input', function(ev) {
            if (ev.target.value === '') {
                secret_key = null;
            } else {
                secret_key = ev.target.value;
            }
            ev.preventDefault();
            ev.stopImmediatePropagation();
            return false;
        });
        secret_key_input.value = secret_key;

        var access_key_input = modify_modal.querySelector('.form-group.access_key input');
        access_key_input.addEventListener('input', function(ev) {
            if (ev.target.value === '') {
                access_key = null;
            } else {
                access_key = ev.target.value;
            }
            ev.preventDefault();
            ev.stopImmediatePropagation();
            return false;
        });
        access_key_input.value = access_key;

        var encrypted_input = modify_modal.querySelector('.form-group.encrypted input');
        encrypted_input.addEventListener('click', function(ev) {
            encrypted = ev.target.checked;
            //ev.preventDefault();
            //ev.stopImmediatePropagation();
            return false;
        });
        encrypted_input.checked = encrypted;

        var submit_button = modify_modal.querySelector('.modal-footer button.modify');
        submit_button.addEventListener('click', function(ev) {
            osfHelpers.putJSON(self.account_url, {
                id: account.id,
                host: host,
                port: port,
                encrypted: encrypted,
                access_key: access_key,
                secret_key: secret_key,
                nickname: nickname
            }).done(function() {
                self.clearModal();
                $modal.modal('hide');
                self.updateAccounts();
                modify_modal.remove();
            }).fail(function(error) {
                self.changeMessage(language.userSettingsError, 'text-danger');
                Raven.captureMessage('Error while updating addon account', {
                extra: {
                    url: url,
                    status: status,
                    error: error
                }
                });
            });
            ev.preventDefault();
            ev.stopImmediatePropagation();
            return false;
        });

        var cancel_button = modify_modal.querySelector('.modal-footer button.cancel');
        cancel_button.addEventListener('click', function(ev) {
            modify_modal.remove();
            ev.preventDefault();
            ev.stopImmediatePropagation();
            return false;
        });

    };

    self.disconnectAccount = function(account) {
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
                extra: {
                    url: url,
                    status: status,
                    error: error
                }
            });
        });
        return request;
    };

    self.selectionChanged = function() {
        self.changeMessage('','');
    };

    self.updateAccounts();
}

$.extend(ViewModel.prototype, ChangeMessageMixin.prototype);

function S3UserConfig(selector, url) {
    // Initialization code
    var self = this;
    self.selector = selector;
    self.url = url;
    // On success, instantiate and bind the ViewModel
    self.viewModel = new ViewModel(url);
    osfHelpers.applyBindings(self.viewModel, self.selector);
}

module.exports = {
    S3ViewModel: ViewModel,
    S3UserConfig: S3UserConfig
};
