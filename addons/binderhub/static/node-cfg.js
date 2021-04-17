'use strict';

var $ = require('jquery');
var m = require('mithril');
var ko = require('knockout');
var Raven = require('raven-js');
var osfHelpers = require('js/osfHelpers');
var ChangeMessageMixin = require('js/changeMessage');
var SaveManager = require('js/saveManager');

var SHORT_NAME = 'binderhub';
var logPrefix = '[' + SHORT_NAME + '] ';


function NodeSettings() {
  var self = this;
  self.baseUrl = window.contextVars.node.urls.api + SHORT_NAME + '/';

  self.binderUrl = ko.observable('');

  ChangeMessageMixin.call(self);

  self.loadConfig = function() {
    var url = self.baseUrl + 'settings';
    console.log(logPrefix, 'loading: ', url);

    return $.ajax({
      url: url,
      type: 'GET',
      dataType: 'json'
    }).done(function (data) {
      console.log(logPrefix, 'loaded: ', data);
      self.binderUrl(data.binder_url);
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
}

$.extend(NodeSettings.prototype, ChangeMessageMixin.prototype);

var settings = new NodeSettings();
osfHelpers.applyBindings(settings, '#' + SHORT_NAME + 'Scope');
settings.loadConfig();
