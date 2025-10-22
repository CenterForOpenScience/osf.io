'use strict';

var $ = require('jquery');
var m = require('mithril');
var ko = require('knockout');
var Raven = require('raven-js');
var osfHelpers = require('js/osfHelpers');
var SaveManager = require('js/saveManager');
var BinderHubHostSettingsMixin = require('./hosts');

var SHORT_NAME = 'binderhub';
var logPrefix = '[' + SHORT_NAME + '] ';


function NodeSettings() {
  var self = this;
  self.baseUrl = window.contextVars.node.urls.api + SHORT_NAME + '/';
  self.userBaseUrl = '/api/v1/settings/' + SHORT_NAME + '/';

  self.loading = ko.observable(false);

  self.binderUrl = ko.observable('');

  self.availableBinderhubs = ko.observableArray();

  self.userBinderhubs = ko.observableArray();

  self.systemBinderhubs = ko.observableArray();

  self.selectedHost = ko.observable('');

  self.presetHosts = ko.computed(function() {
    var hosts = [];
    hosts = hosts.concat(self.userBinderhubs().filter(function(host) {
      return self.availableBinderhubs().filter(function(x) {
        return x.binderhub_url === host.binderhub_url;
      }).length === 0;
    }).map(function(host) {
      return Object.assign({}, host, {
        binderhub_name: host.binderhub_url + ' (User)',
      });
    }));
    hosts = hosts.concat(self.systemBinderhubs().filter(function(host) {
      return self.availableBinderhubs().filter(function(x) {
        return x.binderhub_url === host.binderhub_url;
      }).length === 0;
    }).map(function(host) {
      return Object.assign({}, host, {
        binderhub_name: host.binderhub_url + ' (GRDM)',
      });
    }));
    return hosts;
  });

  BinderHubHostSettingsMixin.call(self);

  self.loadConfig = function() {
    var url = self.baseUrl + 'settings';
    console.log(logPrefix, 'loading: ', url);
    self.loading(true);

    return $.ajax({
      url: url,
      type: 'GET',
      dataType: 'json'
    }).done(function (data) {
      console.log(logPrefix, 'loaded: ', data);
      self.loading(false);
      self.binderUrl(data.binder_url);
      self.availableBinderhubs(data.available_binderhubs);
      self.userBinderhubs(data.user_binderhubs);
      self.systemBinderhubs(data.system_binderhubs);
    }).fail(function(xhr, status, error) {
      Raven.captureMessage('Error while retrieving addon info', {
        extra: {
          url: url,
          status: status,
          error: error
        }
      });
    });
  };

  self.saveConfig = function(callback) {
    var url = self.baseUrl + 'settings';
    console.log(logPrefix, 'saving: ', url);
    return osfHelpers.ajaxJSON(
      'put',
      url,
      {
        data: {
          binder_url: self.binderUrl(),
          available_binderhubs: self.availableBinderhubs()
        }
      }
    ).done(function (data) {
      console.log(logPrefix, 'saved: ', data);
      if (callback) {
        callback();
      }
    }).fail(function(xhr, status, error) {
      Raven.captureMessage('Error while retrieving addon info', {
        extra: {
          url: url,
          status: status,
          error: error
        }
      });
      if (callback) {
        callback();
      }
    });
  };

  self.addUserConfig = function(binderhub, callback) {
    var url = self.userBaseUrl + 'settings';
    console.log(logPrefix, 'adding: ', url);
    return osfHelpers.ajaxJSON(
      'post',
      url,
      {
        data: {
          binderhub: binderhub
        }
      }
    ).done(function (data) {
      console.log(logPrefix, 'added: ', data);
      if (callback) {
        callback();
      }
    }).fail(function(xhr, status, error) {
      Raven.captureMessage('Error while retrieving addon info', {
        extra: {
          url: url,
          status: status,
          error: error
        }
      });
      if (callback) {
        callback();
      }
    });
  };

  /** Default URL changed  */
  self.updateDefaultUrl = function(binderhub) {
    self.binderUrl(binderhub.binderhub_url);
    self.saveConfig();
  }

  /** Add host to binderhub list */
  self.addHost = function() {
    var newHost = self.binderhubConfig();
    self.clearModal();
    $('#binderhubInputHost').modal('hide');
    self.availableBinderhubs.push(newHost);
    self.saveConfig(function() {
      self.addUserConfig(newHost, function() {
        $('#binderhubInputHost').modal('hide');
      });
    });
  };

  /* Remove host from binderhub list */
  self.removeHost = function(host) {
    const removed = self.availableBinderhubs().find(function(binderhub) {
      return binderhub.binderhub_url === host.binderhub_url;
    });
    if (typeof removed === "undefined") {
      return;
    }
    self.availableBinderhubs.remove(removed);
    var url = self.baseUrl + 'settings/binderhubs';
    return osfHelpers.ajaxJSON(
      'delete',
      url,
      {
        data: {
          url: host.binderhub_url
        }
      }
    ).done(function(data) {
      if(host.binderhub_url === self.binderUrl()) {
        self.updateDefaultUrl(self.availableBinderhubs()[0]);
      }
    }
    ).fail(function(xhr, status, error) {
      Raven.captureMessage('Error while deleting a binderhub from a node', {
        extra: {
          url: url,
          status: status,
          error: error
        }
      });
    });
  };

  /** Add preset host to binderhub list */
  self.addPresetHost = function() {
    var newHost = self.findBinderhubByURL(self.selectedHost());
    self.clearPresetModal();
    self.availableBinderhubs.push(newHost);
    self.saveConfig(function() {
      $('#binderhubInputPresetHost').modal('hide');
    });
  };

  self.findBinderhubByURL = function(binderhub_url, binderhubs) {
    if (!binderhubs) {
      var r = self.findBinderhubByURL(binderhub_url, self.userBinderhubs());
      if (r) {
        return r;
      }
      return self.findBinderhubByURL(binderhub_url, self.systemBinderhubs());
    }
    var cands = binderhubs.filter(function(binderhub) {
      return binderhub.binderhub_url === binderhub_url;
    });
    return cands.length > 0 ? cands[0] : null;
  };

  self.clearPresetModal = function() {
      var self = this;
      self.selectedHost(null);
  };

}

$.extend(NodeSettings.prototype, BinderHubHostSettingsMixin.prototype);

var settings = new NodeSettings();
osfHelpers.applyBindings(settings, '#' + SHORT_NAME + 'Scope');
settings.loadConfig();
