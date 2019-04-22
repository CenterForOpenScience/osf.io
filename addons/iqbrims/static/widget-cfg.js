'use strict';

var $ = require('jquery');
var m = require('mithril');
var ko = require('knockout');
var Raven = require('raven-js');
var osfHelpers = require('js/osfHelpers');
var language = require('js/osfLanguage').Addons.iqbrims;

var logPrefix = '[iqbrims] ';


function IQBRIMSWidget() {
  var self = this;
  self.baseUrl = window.contextVars.node.urls.api + 'iqbrims/';
  self.loading = ko.observable(true);
  self.loadFailed = ko.observable(false);
  self.loadCompleted = ko.observable(false);
  self.modeDeposit = ko.observable(false);
  self.modeCheck = ko.observable(false);
  self.depositHelp = ko.observable(language.depositHelp);
  self.checkHelp = ko.observable(language.checkHelp);

  self.loadConfig = function() {
    var url = self.baseUrl + 'status';
    console.log(logPrefix, 'loading: ', url);

    return $.ajax({
        url: url,
        type: 'GET',
        dataType: 'json'
    }).done(function (data) {
      console.log(logPrefix, 'loaded: ', data);
      var status = data['data']['attributes'];
      if (status['state'] == 'deposit') {
        self.modeDeposit(true);
        self.modeCheck(false);
      } else if (status['state'] == 'check') {
        self.modeDeposit(false);
        self.modeCheck(true);
      } else {
        self.modeDeposit(false);
        self.modeCheck(false);
      }
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

  self.gotoCheckForm = function() {
    window.location.href = './iqbrims#check';
  };

  self.gotoDepositForm = function() {
    window.location.href = './iqbrims#deposit';
  };

  self.clearModal = function() {
    console.log('Clear Modal');
  };

}

var w = new IQBRIMSWidget();
osfHelpers.applyBindings(w, '#iqbrims-content');
w.loadConfig();
