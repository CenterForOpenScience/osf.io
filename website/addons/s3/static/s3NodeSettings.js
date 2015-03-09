'use strict';

var ko = require('knockout');
require('knockout-punches');
require('knockout-mapping');
var $ = require('jquery');
var bootbox = require('bootbox');
var Raven = require('raven-js');

var $osf = require('osfHelpers');

ko.punches.enableAll();

var ViewModel = function(url, selector) {
    var self = this;

    self.url = url;
    self.selector = selector;

    self.nodeHasAuth = ko.observable(false);
    self.userHasAuth = ko.observable(false);
    self.userIsOwner = ko.observable(false);
    self.ownerName = ko.observable('');

    self.urls = ko.observable({});
    self.loadedSettings = ko.observable(false);
    self.bucketList = ko.observable([]);
    self.loadedBucketList = ko.observable(false);
    self.currentBucket = ko.observable('');
    self.selectedBucket = ko.observable('');

    self.accessKey = ko.observable('');
    self.password = ko.observable('');

    self.loading = ko.observable(false);
    self.creating = ko.observable(false);

    self.message = ko.observable('');
    self.messageClass = ko.observable('text-info');

    self.showSelect = ko.observable(false);

    self.showSettings = ko.pureComputed(function() {
        return self.nodeHasAuth();
    });
    self.disableSettings = ko.pureComputed(function() {
        return !(self.userHasAuth() && self.userIsOwner());
    });
    self.showNewBucket = ko.pureComputed(function() {
        return self.userHasAuth() && self.userIsOwner();
    });
    self.showImport = ko.pureComputed(function() {
        return self.userHasAuth() && !self.nodeHasAuth();
    });
    self.showCreateCredentials = ko.pureComputed(function(){
        return !self.nodeHasAuth() && !self.userHasAuth();
    });
    self.canChange = ko.pureComputed(function(){
        return self.userIsOwner() && self.nodeHasAuth();
    });

    self.fetchFromServer();
};

ViewModel.prototype.toggleSelect = function(){
    this.showSelect(!this.showSelect());
    if (!this.loadedBucketList()){
        this.fetchBucketList();
        this.loadedBucketList(true);
    }
};

ViewModel.prototype.selectBucket = function(){    
    var self = this;
    self.loading(true);
    $osf.postJSON(
        self.urls().setBucket,
        {
            's3_bucket': self.selectedBucket()
        }
    )
        .done(function(response){
            self.updateFromData(response);
            var filesUrl = window.contextVars.node.urls.web + 'files/';
            self.changeMessage('Successfully linked S3 bucket \'' + self.currentBucket() + '\'. Go to the <a href="' +
                               filesUrl + '">Files page</a> to view your content.', 'text-success');
            self.loading(false);
        })
        .fail(function(xhr, status, error){
            self.loading(false);
            $osf.handleJSONError(xhr, status, error);
        });
};

ViewModel.prototype.deauthorizeNode = function(){
    var self = this;

    bootbox.confirm({
        title: 'Deauthorize S3?',
        message: 'Are you sure you want to remove this S3 authorization?',
        callback: function(confirm) {
            if(confirm) {
                $.ajax({
                    type: 'DELETE',
                    url: self.urls().deauthorize,
                    contentType: 'application/json',
                    dataType: 'json'
                }).done(function(response) {
                    self.updateFromData(response);
                }).fail(
                    $osf.handleJSONError
                );
            }
        }
    });    
};

ViewModel.prototype.importAuth = function() {
    var self = this;
    $osf.postJSON(
        self.urls().importAuth,
        {}
    ).done(function(response) {
        self.updateFromData(response);
    }).fail(
        $osf.handleJSONError
    );
    
};

ViewModel.prototype.createCredentials = function() {

};

ViewModel.prototype.createBucket = function(bucketName){
    var self = this;
    self.creating(true);
    $osf.postJSON(
        self.urls().createBucket, 
        {
            bucket_name: bucketName
        }
    ).done(function(response) {
        self.creating(false);
        self.updateFromData(response);
        self.changeMessage('Successfully created bucket. You can now select it from the dropdown of buckets.', 'text-success');
        self.showSelect(true);
    }).fail(function(xhr) {
        var message = JSON.parse(xhr.responseText).message;
        self.creating(false);
        if (!message) {
            message = 'Looks like that name is taken. Try another name?';
        }
        bootbox.confirm({
            title: 'Duplicate bucket name',
            message: message,
            callback: function(result) {
                if (result) {
                    self.openCreateBucket();
                }
            }
        });
    });

};

ViewModel.prototype.fetchBucketList = function(){
    var self = this;
    $.ajax({
        url: self.urls().bucketList,
        type: 'GET',
        dataType: 'application/json'
    })
        .done(function(response){
            self.bucketList(response);
        })
        .fail(function(xhr, status, error){
            
        });

};

ViewModel.prototype.openCreateBucket = function() {
    var self = this;

    var isValidBucket = /^(?!.*(\.\.|-\.))[^.][a-z0-9\d.-]{2,61}[^.]$/;

    bootbox.prompt('Name your new bucket', function(bucketName) {
        if (!bucketName) {
            return;
        } else if (isValidBucket.exec(bucketName) == null) {
            bootbox.confirm({
                title: 'Invalid bucket name',
                message: 'Sorry, that\'s not a valid bucket name. Try another name?',
                callback: function(result) {
                    if (result) {
                        self.openCreateBucket(bucketName);
                    }
                }
            });
        } else {
            bucketName = bucketName.toLowerCase();
            self.createBucket(bucketName);
        }
    });
};

ViewModel.prototype.updateFromData = function(settings){
    var self = this;
    self.nodeHasAuth(settings.node_has_auth);
    self.userHasAuth(settings.user_has_auth);            
    self.userIsOwner(settings.user_is_owner);
    self.ownerName(settings.owner);
    self.currentBucket(settings.has_bucket ? settings.bucket : 'None');
    self.bucketList(settings.bucket_list);
    self.loadedSettings(true);
    if (settings.urls){
        self.urls(settings.urls);
    }  
};

ViewModel.prototype.fetchFromServer = function() {
    var self = this;
    var request = $.ajax({
            url: self.url,
            type: 'GET',
            dataType: 'json'
        })
        .done(function(response) {
            var settings = response.result;
            self.updateFromData(settings);
            if (self.nodeHasAuth() && (self.bucketList() === null)) {
                if (self.userIsOwner()) {
                    //self.changeMessage();
                } else {
                    //self.changeMessage();
                }
            }
        })
        .fail(function(xhr, status, error) {
            //self.changeMessage(self.messages.CANT_RETRIEVE_SETTINGS(), 'text-warning');
            Raven.captureMessage('Could not GET s3 settings', {
                url: self.url,
                textStatus: status,
                error: error
            });
        });
};

/** Change the flashed message. */
ViewModel.prototype.changeMessage = function(text, css, timeout) {
    var self = this;
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

var S3Config = function(selector, url){   
    var viewModel = new ViewModel(url, selector);
    $osf.applyBindings(viewModel, selector);
};

module.exports = S3Config;
