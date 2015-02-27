/**
* View model that controls the Google Drive configuration on the user settings page.
*/
'use strict';

var ko = require('knockout');
require('knockout-punches');
ko.punches.enableAll();
var $ = require('jquery');
var Raven = require('raven-js');
var bootbox = require('bootbox');

var language = require('osfLanguage').Addons.googledrive;
var osfHelpers = require('osfHelpers');

var ViewModel = function(url) {
    var self = this;
    self.userHasAuth = ko.observable(false);
    self.loaded = ko.observable(false);
    self.urls = ko.observable();
    self.username = ko.observable();

    //Helper-class variables
    self.message = ko.observable('');
    self.messageClass = ko.observable('text-info');

    $.ajax({
        url: url,
        type: 'GET',
        dataType: 'json',
    }).done(function(response) {
        var data =response.result;
        self.userHasAuth(data.userHasAuth);
        self.username(data.username);
        self.urls(data.urls);
        self.loaded(true);
    }).fail(function(xhr, textStatus, error) {
        self.changeMessage(
            'Could not retrieve settings. Please refresh the page or ' +
            'contact <a href="mailto: support@osf.io">support@osf.io</a> if the ' +
            'problem persists.', 'text-warning'
        );
        Raven.captureMessage('Could not GET Google Drive settings', {
            url: url,
            textStatus: textStatus,
            error: error
        });
    });

    /** Change the flashed status message */
    self.changeMessage = function(text, css, timeout) {
        self.message(text);
        var cssClass = css || 'text-info';
        self.messageClass(cssClass);
        if (timeout) {
            // Reset message after timeout period
            setTimeout(function() {
                self.message('');
                self.messageClass('text-info');
            }, timeout);
        }
    };

    /** Create Authorization **/
    self.createAuth = function(){
        $.osf.postJSON(
            self.urls().create
        ).success(function(response){
            window.location.href = response.url;
            //TODO: Find a way to display this message
            //self.changeMessage('Successfully authorized Google Drive account', 'text-primary');
        }).fail(function(){
            self.changeMessage('Could not authorize at this moment', 'text-danger');
        });
    };

    /** Pop up confirm dialog for deleting user's access token. */
    self.deleteKey = function() {
        bootbox.confirm({
            title: 'Delete Google Drive Token?',
            message: language.confirmDeauth,
            callback: function(confirmed) {
                if (confirmed) {
                    sendDeauth();
                }
            }
        });
    };

    /** Send DELETE request to deauthorize Drive */
    function sendDeauth() {
        return $.ajax({
            url: self.urls().delete,
            type: 'DELETE'
        }).done(function() {
            window.location.reload();
            self.changeMessage(language.deauthSuccess, 'text-info', 5000);
        }).fail(function(textStatus, error) {
            self.changeMessage(language.deauthError, 'text-danger');
            Raven.captureMessage('Could not deauthorize Google Drive.', {
                url: url,
                textStatus: textStatus,
                error: error
            });
        });
    }
};

function GoogleDriveUserConfig(selector, url) {
    // Initialization code
    var self = this;
    self.viewModel = new ViewModel(url);
    $.osf.applyBindings(self.viewModel, selector);
}

module.exports = GoogleDriveUserConfig;
