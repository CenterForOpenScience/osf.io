'use strict';

var $ = require('jquery');
var m = require('mithril');
var ko = require('knockout');
var Raven = require('raven-js');
var osfHelpers = require('js/osfHelpers');
var ChangeMessageMixin = require('js/changeMessage');
var SaveManager = require('js/saveManager');

var SHORT_NAME = 'myskelton';
var logPrefix = '[' + SHORT_NAME + '] ';


function NodeSettings() {
  var self = this;
  self.baseUrl = window.contextVars.node.urls.api + SHORT_NAME + '/';

  self.param_1 = ko.observable('');
  self.loaded_param_1 = ko.observable('');
  self.dirty = ko.computed(function() {
    return self.param_1() != self.loaded_param_1();
  })

  ChangeMessageMixin.call(self);

  self.saveManager = new SaveManager(
    self.baseUrl + 'settings',
    null,
    {
      dirty: function() {
        return self.param_1() != self.loaded_param_1()
      }
    }
  );

  self.submit = function() {
    console.log(logPrefix, 'submit', self.param_1());
    self.saveManager.save({'param_1': self.param_1()})
      .then(function (data) {
        console.log(logPrefix, 'updated: ', data);
        self.loaded_param_1(self.param_1())
      },
      function(reason) {
        Raven.captureMessage('Error while updating addon info', {
          extra: {
            reason: reason
          }
        });
      })
  };

  self.loadConfig = function() {
    var url = self.baseUrl + 'settings';
    console.log(logPrefix, 'loading: ', url);

    return $.ajax({
      url: url,
      type: 'GET',
      dataType: 'json'
    }).done(function (data) {
      console.log(logPrefix, 'loaded: ', data);
      self.loaded_param_1(data.param_1);
      self.param_1(data.param_1);
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
