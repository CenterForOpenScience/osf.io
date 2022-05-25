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


function UserSettings() {
  var self = this;
  self.properName = 'GakuNin Federated Computing Services (Jupyter)';
  self.baseUrl = '/api/v1/settings/' + SHORT_NAME + '/';

  self.loading = ko.observable(false);

  self.binderhubs = ko.observableArray();

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
      self.binderhubs(data.binderhubs);
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
          binderhubs: self.binderhubs()
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

  /** Add host to binderhub list */
  self.addHost = function() {
    var newHost = self.binderhubConfig();
    self.clearModal();
    self.binderhubs.push(newHost);
    self.saveConfig(function() {
      $('#binderhubInputHost').modal('hide');
    });
  };

  /* Remove host from binderhub list */
  self.removeHost = function(host) {
    const removed = self.binderhubs().filter(function(binderhub) {
      return binderhub.binderhub_url === host.binderhub_url;
    });
    console.log('Host', host, removed);
    if (removed.length < 1) {
      return;
    }
    self.binderhubs.remove(removed[0]);
    self.saveConfig();
  };

}

$.extend(UserSettings.prototype, BinderHubHostSettingsMixin.prototype);

var settings = new UserSettings();
osfHelpers.applyBindings(settings, '#' + SHORT_NAME + 'Scope');
settings.loadConfig();
