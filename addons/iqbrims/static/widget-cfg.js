'use strict';

var $ = require('jquery');
var m = require('mithril');
var ko = require('knockout');
var Raven = require('raven-js');
var osfHelpers = require('js/osfHelpers');

var logPrefix = '[iqbrims] ';


function IQBRIMSWidget() {
  var self = this;
  self.baseUrl = window.contextVars.node.urls.api + 'iqbrims/';
  self.loading = ko.observable(true);
  self.loadFailed = ko.observable(false);
  self.loadCompleted = ko.observable(false);
  self.status = ko.observable('');

  self.loadConfig = function() {
    var url = self.baseUrl + 'status';
    console.log(logPrefix, 'loading: ', url);

    return $.ajax({
        url: url,
        type: 'GET',
        dataType: 'json'
    }).done(function (data) {
      console.log(logPrefix, 'loaded: ', data);
      services = data.data;
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

  self.clearModal = function() {
    console.log('Clear Modal');
  };

}

var w = new IQBRIMSWidget();
osfHelpers.applyBindings(w, '#iqbrims-content');
w.loadConfig();
