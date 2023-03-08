/**
 * Module that controls the Metadata node settings. Includes Knockout view-model
 * for syncing data.
 */

const ko = require('knockout');
const Raven = require('raven-js');

const $osf = require('js/osfHelpers');
const ChangeMessageMixin = require('js/changeMessage');

const _ = require('js/rdmGettext')._;


const INTERVAL_NODE_SETTINGS = 500;
const MAX_RETRY_NODE_SETTINGS = 10;
const logPrefix = '[metadata]';

const $modal = $('#metadataApplyDialog');

function initHooks(nodeId, addons, callback) {
    if (!addons || addons.length === 0) {
        return;
    }
    const prefixes = addons.map(function(addon) {
        return '/api/v1/project/' + nodeId + '/' + addon.name + '/';
    });
    console.log(logPrefix, 'initHooks', prefixes);
    (function() {
        var origOpen = XMLHttpRequest.prototype.open;
        XMLHttpRequest.prototype.open = function(method, url) {
            this.addEventListener('load', function() {
                if (prefixes.every(function(prefix) {
                    return !url.startsWith(prefix);
                })) {
                    return;
                }
                const targetAddon = addons[prefixes.findIndex(function(prefix) {
                    return url.startsWith(prefix);
                })];
                console.log(logPrefix, 'HTTP Request Completed: ', targetAddon, url);
                callback(targetAddon);
            });
            origOpen.apply(this, arguments);
        };
    })();
}


function ViewModel(nodeId, url) {
    const self = this;
    ChangeMessageMixin.call(self);

    self.addonName = 'Metadata';
    self.nodeId = nodeId;
    self.url = url;
    self.urls = ko.observable();

    self.loadedSettings = ko.observable(false);
    self.importedAddonSettings = ko.observableArray([]);

    self.applicableAddonSettings = ko.computed(function() {
        return self.importedAddonSettings().filter(function(setting) {
            return setting.applicable && !setting.applied;
        });
    });
    self.nonApplicableAddonSettings = ko.computed(function() {
        return self.importedAddonSettings().filter(function(setting) {
            return !setting.applicable;
        });
    });
    self.incompletedAddonSettings = ko.computed(function() {
        return self.importedAddonSettings().filter(function(setting) {
            return !setting.applied;
        });
    });

    self.refresh(function() {
        const addons = [];
        initHooks(self.nodeId, self.importedAddonSettings(), function(targetAddon) {
            console.log(logPrefix, 'initHooks callback', targetAddon);
            self.waitForAddonSetting(targetAddon, function(addons) {
                const nonAppliedAddons = addons.filter(function(addon) {
                    return !addon.applied;
                });
                if (nonAppliedAddons.length === 0) {
                    return;
                }
                $modal.modal('show');
            });
        });
    });
}

$.extend(ViewModel.prototype, ChangeMessageMixin.prototype);

ViewModel.prototype.refresh = function(callback) {
    const self = this;
    $.ajax({
        url: self.url,
        type: 'GET',
        dataType: 'json'
    }).done(function(response) {
        const importedAddonSettings = response.data.attributes.imported_addon_settings || [];
        self.importedAddonSettings(importedAddonSettings);
        self.loadedSettings(true);
        if (!callback) {
            return;
        }
        callback();
    }).fail(function(xhr, textStatus, error) {
        self.changeMessage(_('Could not GET metadata settings'), 'text-danger');
        Raven.captureMessage('Could not GET metadata settings', {
            extra: {
                url: self.url,
                textStatus: textStatus,
                error: error
            }
        });
    });
};

ViewModel.prototype.waitForAddonSetting = function(targetAddon, callback) {
    const self = this;
    var retry = MAX_RETRY_NODE_SETTINGS;
    const interval = setInterval(function() {
        self.refresh(function() {
            const setting = self.importedAddonSettings().filter(function(setting) {
                return setting.applicable && setting.name === targetAddon.name;
            });
            if (setting.length === 0 && retry > 0) {
                retry --;
                return;
            }
            console.log(logPrefix, 'Settings updated', setting);
            clearInterval(interval);
            if (setting && callback) {
                callback(setting);
            }
        });
    }, INTERVAL_NODE_SETTINGS);
};

ViewModel.prototype.applyAddonSettings = function() {
    const self = this;
    $osf.putJSON(
        self.url,
        {
            addons: self.applicableAddonSettings().map(function(addon) {
                return addon.name;
            }),
        }
    )
        .then(function() {
            self.changeMessage(_('Add-on settings applied.'), 'text-success');
            setTimeout(function() {
                window.location.reload();
            }, 1000)
        })
        .catch(function(xhr, textStatus, error) {
            self.changeMessage(_('Failed to apply add-on settings.'), 'text-danger')
            Raven.captureMessage('Failed to apply add-on settings.', {
                extra: {
                    url: self.url,
                    textStatus: textStatus,
                    error: error
                }
            });
        });

    $modal.modal('hide');
};

function MetadataNodeConfig(selector, nodeId, url) {
    // Initialization code
    const self = this;
    self.nodeId = nodeId;
    self.url = url;
    // On success, instantiate and bind the ViewModel
    self.viewModel = new ViewModel(nodeId, url);
    $osf.applyBindings(self.viewModel, selector);
}

module.exports = MetadataNodeConfig;
