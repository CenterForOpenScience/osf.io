'use strict';

var ko = require('knockout');
require('knockout.punches');
var $ = require('jquery');
var bootbox = require('bootbox');
var Raven = require('raven-js');

var $osf = require('js/osfHelpers');

ko.punches.enableAll();

var flatAddonViewModel = function(url, selector, addonName, folderType, opts) {
	var self = this;

	self.url = url;
	self.selector = selector;
	self.addonName = addonName;
	self.folderType = folderType;
	
	self.nodeHasAuth = ko.observable(false);
	self.userHasAuth = ko.observable(false);
	self.userIsOwner = ko.observable(false);
	self.ownerName = ko.observable('');

    self.accounts = ko.observable([]);
	self.urls = ko.observable({});
	self.loadedSettings = ko.observable(false);
	self.folderList = ko.observableArray([]);
	self.loadedFolderList = ko.observable(false);
	self.currentFolder = ko.observable('');
	self.selectedFolder = ko.observable('');

	self.loading = ko.observable(false);
	self.creating = ko.observable(false);
	self.creatingCredentials = ko.observable(false);

    self.message = ko.observable('');
    self.messageClass = ko.observable('text-info');

    self.showSelect = ko.observable(false);

    self.validCredentials = ko.observable(false);

    self.showSettings = ko.pureComputed(function() {
        return self.nodeHasAuth();
    });
    self.disableSettings = ko.pureComputed(function() {
        return !(self.userHasAuth() && self.userIsOwner());
    });
    self.showNewFolder = ko.pureComputed(function() {
        return self.userHasAuth() && self.userIsOwner();
    });
    self.showImport = ko.pureComputed(function() {
        return self.userHasAuth() && !self.nodeHasAuth();
    });
    self.showCreateCredentials = ko.pureComputed(function() {
        return self.loadedSettings() && (!self.nodeHasAuth() && !self.userHasAuth());
    });
    self.canChange = ko.pureComputed(function() {
        return self.userIsOwner() && self.nodeHasAuth();
    });
    self.allowSelectFolder = ko.pureComputed(function() {
        return (self.folderList().length > 0 || self.loadedFolderList()) && (!self.loading());
    });

    var defaults = {
    	formatFolders : function(response) {
    		return response
    	},
    	formatFolderName : function(folderName) {
    		return folderName
    	},
    	fixBadName : function(newName, folderName, self) {
    		bootbox.dialog({
    			title: 'Invalid ' + folderType + ' name',
    			message: 'Sorry, that\'s not a valid ' + folderType + 'name. Try another name?',
                callback: function(result) {
                    if (result) {
                        self.openCreateFolder();
                    }
                }
    		});
    	},
        attemptRetrieval : function(settings) {
            return
        },
        findFolder : function(settings) {
            return settings.folder
        },
        dataGetSettings: function(data) {
            return data;
        }
    };

    self.options = $.extend({}, defaults, opts);

};

flatAddonViewModel.prototype.toggleSelect = function() {
	var self = this;
	self.showSelect(!self.showSelect());
	return self.updateFolderList();
};

flatAddonViewModel.prototype.updateFolderList = function() {
	var self = this;
	return self.fetchFolderList()
		.done(function(folders){
			self.folderList(folders);
			self.selectedFolder(self.currentFolder());
		});
};

flatAddonViewModel.prototype.fetchFolderList = function() {
	var self = this;

	var ret = $.Deferred();
	if (self.loadedFolderList()) {
		ret.resolve(self.folderList());
	} else {
		$.ajax({
			url: self.urls().repo_list,
			type: 'GET',
			datatype: 'json'
		}).done(function(response) {
			self.loadedFolderList(true);
			var folders = self.options.formatFolders(response); 
			ret.resolve(folders);
		})
		.fail(function(xhr, status, error) {
			var message = 'Could not retrieve list of ' + self.addonName + ' ' + self.folderType + 
				's at this time. Please refresh the page. If the problem persists, email ' +
				'<a href="mailto:support@osf.io">support@osf.io</a>.';
			self.changeMessage(message, 'text-warning');
			Raven.captureMessage('Could not GET ' + self.addonName + ' ' + self.folderType + ' list', {
				url: self.urls().repo_list, //needs to be looked at
				textStatus: status,
				error: error
			});
			ret.reject(xhr, status, error);
		});
	}
	return ret.promise();
};

flatAddonViewModel.prototype.selectFolder = function() {
	var self = this;
	self.loading(true);
	//var url_type = self.addonName + '_' + self.folderType;
	return $osf.postJSON(
			self.urls().config, {
				folder: self.selectedFolder() //FIX THIS CRAP
			}
		)
		.done(function(response) {
			self.updateFromData(response);
			self.changeMessage('Successfully linked ' + self.addonName + ' ' + self.folderType + ' \'' +
					self.currentFolder() + '\'. Go to the <a href="' + self.urls().files +
					'">Files page</a> to view your content.', 'text-success');
			self.loading(false);
		})
		.fail(function(xhr, status, error) {
			self.loading(false);
			var message = 'Could not change ' + self.addonName + ' ' + self.folderType +' at this time. ' +
                'Please refresh the page. If the problem persists, email ' +
                '<a href="mailto:support@osf.io">support@osf.io</a>.';
            self.changeMessage(message, 'text-warning');
            Raven.captureMessage('Could not set ' + self.addonName + ' ' + self.folderType, {
            	url: self.urls().setFolder, //needs to be looked at
            	textStatus: status,
            	error: error
            });
		});
};

flatAddonViewModel.prototype._deauthorizeNodeConfirm = function() {
    var self = this;
    return $.ajax({
        type: 'DELETE',
        url: self.urls().deauthorize,
        contentType: 'application/json',
        dataType: 'json'
    }).done(function(response) {
        self.updateFromData(response);
        self.changeMessage('Successfully deauthorized ' + self.addonName + ' credentials', 'text-success');
    }).fail(function(xhr, status, error) {
        var message = 'Could not deauthorize ' + self.addonName + ' at ' +
            'this time. Please refresh the page. If the problem persists, email ' +
            '<a href="mailto:support@osf.io">support@osf.io</a>.';
        self.changeMessage(message, 'text-warning');
        Raven.captureMessage('Could not remove ' + self.addonName +' authorization.', {
            url: self.urls().deauthorize,
            textStatus: status,
            error: error
        });
    });
};

flatAddonViewModel.prototype.deauthorizeNode = function() {
    var self = this;
    bootbox.confirm({
        title: 'Deauthorize ' + self.addonName + '?',
        message: 'Are you sure you want to remove this ' + self.addonName + ' authorization?',
        callback: function(confirm) {
            if (confirm) {
                self._deauthorizeNodeConfirm();
            }
        }
    });
};

flatAddonViewModel.prototype.updateFromData = function(data) {
    var self = this;
    var ret = $.Deferred();

    var applySettings = function(settings){
        self.nodeHasAuth(settings.nodeHasAuth);
        self.userHasAuth(settings.userHasAuth);
        self.userIsOwner(settings.userIsOwner);
        self.ownerName(settings.owner);
        if (settings.urls) {
            self.urls(settings.urls);
        }
        if ((settings.valid_credentials != null) && (typeof settings.valid_credentials != 'undefined')){
            self.validCredentials(settings.valid_credentials);
        }
        self.currentFolder(self.options.findFolder(settings));
        self.options.attemptRetrieval(settings);
        ret.resolve(settings);
    };
    if (typeof data === 'undefined'){
        return self.fetchFromServer()
            .done(applySettings);
    } else {
        applySettings(self.options.dataGetSettings(data));
    }
    return ret.promise();
};

flatAddonViewModel.prototype.changeMessage = function(text, css, timeout) {
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

flatAddonViewModel.prototype.fetchFromServer = function() {
    var self = this;
    var ret = $.Deferred();
    $.ajax({
            url: self.url,
            type: 'GET',
            dataType: 'json',
            contentType: 'application/json'
        })
        .done(function(response) {
            var settings = response.result;
            self.loadedSettings(true);
            ret.resolve(settings);
        })
        .fail(function(xhr, status, error) {
            var message = 'Could not retrieve ' + self.addonName + ' settings at ' +
                'this time. Please refresh the page. If the problem persists, email ' +
                '<a href="mailto:support@osf.io">support@osf.io</a>.';
            self.changeMessage(message, 'text-warning');
            Raven.captureMessage('Could not GET ' + self.addonName + ' settings', {
                url: self.url,
                textStatus: status,
                error: error
            });
            ret.reject(xhr, status, error);
        });
    return ret.promise();
};

flatAddonViewModel.prototype.createFolder = function(folderName) {
    var self = this;
    self.creating(true);
    folderName = folderName.toLowerCase();
    return $osf.postJSON(
        self.urls().create_repo, {
            repo_name: folderName
        }
    ).done(function(response) {
        self.creating(false);
        var folders = self.options.formatFolders(response);
        self.folderList(folders);
        self.loadedFolderList(true);
        self.selectedFolder(folderName); //Github syntax: self.selectedRepo((self.ownerName() + " / " + repoName));
        self.showSelect(true);
    	var newName = self.options.formatFolderName(folderName);
        var msg = 'Successfully created ' + self.folderType + ' "' + newName +
            '". You can now select it from the drop down list.';
        var msgType = 'text-success';
        self.changeMessage(msg, msgType);
    }).fail(function(xhr) {
        var resp = JSON.parse(xhr.responseText);
        var message = resp.message;
        var title = resp.title || 'Problem creating ' + self.folderType;
        self.creating(false);
        if (!message) {
            message = 'Looks like that name is taken. Try another name?';
        }
        bootbox.confirm({
            title: title,
            message: message,
            callback: function(result) {
                if (result) {
                    self.openCreateFolder();
                }
            }
        });
    });
};

flatAddonViewModel.prototype.openCreateFolder = function(folderName) {
	var self = this;

	bootbox.prompt('Name your new ' + self.folderType, function(folderName) {
		if (!folderName) {
			return;
		} else {
			var newName = self.options.formatFolderName(folderName);
			if (newName != folderName) {
				self.options.fixBadName(newName, folderName, self);
			} else {
				self.createFolder(folderName);
			}
		}
	});
};

flatAddonViewModel.prototype.importAuth = function() {
 var self = this;
    return self.updateAccounts()
        .then(function() {
            if (self.accounts().length > 1) {
                bootbox.prompt({
                    title: 'Choose ' + self.addonName + ' Access Token to Import',
                    inputType: 'select',
                    inputOptions: ko.utils.arrayMap(
                        self.accounts(),
                        function(item) {
                            return {
                                text: item.name,
                                value: item.id
                            };
                        }
                    ),
                    value: self.accounts()[0].id,
                    callback: (self.connectExistingAccount.bind(self))
                });
            } else {
                bootbox.confirm({
                    title: 'Import ' + self.addonName + ' Access Token?',
                    message: 'Are you sure you want to authorize this project with your ' + self.addonName +
                        ' access token?',
                    callback: function(confirmed) {
                        if (confirmed) {
                            self.connectExistingAccount.call(self, (self.accounts()[0].id));
                        }
                    }
                });
            }
        });
};

//For flat addons with multiple possible connected accounts
flatAddonViewModel.prototype.updateAccounts = function() {
    var self = this;
    return self.fetchAccounts()
        .done(function(accounts) {
            self.accounts(
                $.map(accounts, function(account) {
                    return {
                        name: account.display_name,
                        id: account.id
                    };
                })
            );
        });
};

flatAddonViewModel.prototype.fetchAccounts = function() {
    var self = this;
    var ret = $.Deferred();
    var request = $.get(self.urls().accounts); //make sure urls() has accounts
    request.then(function(data) {
        ret.resolve(data.accounts);
    });
    request.fail(function(xhr, status, error) {
        self.changeMessage('Could not retrieve ' + self.addonName + ' account list at '+
            'this time. Please refresh the page. If the problem persists, email '+
            '<a href="mailto:support@osf.io">support@osf.io</a>.', 'text-warning');
        Raven.captureMessage('Could not GET ' + self.addonName + 'accounts for user', {
            url: self.url,
            textStatus: status,
            error: error
        });
        ret.reject(xhr, status, error);
    });
    return ret.promise();
};

flatAddonViewModel.prototype.connectAccount = function() {
    var self = this;

    window.oauthComplete = function(res) {
        self.changeMessage('Successfully created a ' + self.addonName + ' access token', 'text-success', 3000);
        self.importAuth.call(self);
    };
    window.open(self.urls().auth);
};

flatAddonViewModel.prototype.connectExistingAccount = function(account_id) {
    var self = this;
    return $osf.putJSON(
        self.urls().importAuth, {
            external_account_id: account_id
        }
    ).done(function(response) {
        self.changeMessage('Successfully imported ' + self.addonName + ' credentials.', 'text-success');
        self.updateFromData(response);
    }).fail(function(xhr, status, error) {
        var message = 'Could not import ' + self.addonName + ' credentials at this time.' +
            ' Please refresh the page. If the problem persists, email ' +
            '<a href="mailto:support@osf.io">support@osf.io</a>';
        self.changeMessage(message, 'text-warning');
        Raven.captureMessage('Could not import ' + self.addonName + ' credentials', {
            url: self.urls().importAuth,
            textStatus: status,
            error: error
        });
    });
};

module.exports = {
    FlatNodeConfig: FlatNodeConfig,
    _flatNodeConfig: flatAddonViewModel
};

function FlatNodeConfig(addonName, selector, url, folderType, opts) {
    var self = this;
    self.url = url;
    if (typeof opts === 'undefined') {
        opts = {};
    }
    self.viewModel = new flatAddonViewModel(url, selector, addonName, folderType, opts);
    self.viewModel.updateFromData();
    $osf.applyBindings(self.viewModel, selector);
}
