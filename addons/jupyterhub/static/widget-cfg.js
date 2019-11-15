'use strict';

var $ = require('jquery');
var ko = require('knockout');
var Raven = require('raven-js');
var osfHelpers = require('js/osfHelpers');

var logPrefix = '[jupyterhub] ';


function JupyterWidget() {
  var self = this;
  self.baseUrl = window.contextVars.node.urls.api + 'jupyterhub/';
  self.loading = ko.observable(true);
  self.loadFailed = ko.observable(false);
  self.loadCompleted = ko.observable(false);
  self.availableServices = ko.observableArray();
  self.availableLinks = ko.observableArray();

  self.loadConfig = function() {
    var url = self.baseUrl + 'services';
    console.log(logPrefix, 'loading: ', url);

    return $.ajax({
        url: url,
        type: 'GET',
        dataType: 'json'
    }).done(function (data) {
      console.log(logPrefix, 'loaded: ', data);
      self.availableServices(data.data);
      self.loading(false);
      self.loadCompleted(true);
    }).fail(function(xhr, status, error) {
      self.loading(false);
      self.loadFailed(true);
      Raven.captureMessage('Error while retrieving addon info', {
          extra: {
              url: url,
              status: status,
              error: error
          }
      });
    });
  };

}

var w = new JupyterWidget();
osfHelpers.applyBindings(w, '#jupyterhubLinks');
w.loadConfig();
