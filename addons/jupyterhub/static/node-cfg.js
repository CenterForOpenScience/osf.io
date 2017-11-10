'use strict';

var $ = require('jquery');
var m = require('mithril');
var ko = require('knockout');
var Fangorn = require('js/fangorn').Fangorn;
var Raven = require('raven-js');
var osfHelpers = require('js/osfHelpers');
var ChangeMessageMixin = require('js/changeMessage');
var SaveManager = require('js/saveManager');

var logPrefix = '[jupyterhub] ';


function JupyterNodeSettings() {
  var self = this;
  self.baseUrl = window.contextVars.node.urls.api + 'jupyterhub/';
  self.serviceName = ko.observable('');
  self.serviceBaseUrl = ko.observable('');
  self.disabled = ko.observable(false);
  self.dirtyCount = ko.observable(0);

  self.services = ko.observableArray();

  ChangeMessageMixin.call(self);

  self.editing = null;
  self.saveManager = new SaveManager(
      self.baseUrl + 'settings',
      null, {
          dirty: self.dirtyCount
      }
  );

  self.urlPattern = /^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b([-a-zA-Z0-9@:%_\+.~#?&//=]*)$/;

  self.removeService = function(service) {
    console.log('Remove service: ', service.id);
    self.services.remove(function(item) { return item.id == service.id });
    self.dirtyCount(self.dirtyCount() + 1);
  };

  self.editService = function(service) {
    console.log('Edit service: ', service.id);
    self.editing = service;
    self.serviceName(service.data.name);
    self.serviceBaseUrl(service.data.base_url);
    $('#jupyterServiceDialog').modal('show');
  };

  self.clearModal = function() {
    self.editing = null;
    self.serviceName('');
    self.serviceBaseUrl('');
    self.message('');
    self.messageClass('text-info');
    $('#jupyterServiceDialog').modal('hide');
  };

  self.submitService = function() {
    if(! self.serviceName()) {
      self.changeMessage('Please enter Name of JupyterHub.', 'text-danger');
      return;
    }
    if(! self.serviceBaseUrl()) {
      self.changeMessage('Please enter URL of JupyterHub.', 'text-danger');
      return;
    }
    if(! self.urlPattern.test(self.serviceBaseUrl())) {
      self.changeMessage('Please enter Valid URL of JupyterHub.', 'text-danger');
      return;
    }
    if(self.editing === null) {
      var newId = Math.max.apply(null, self.services().map(function(e) {
        return e.id;
      })) + 1;
      console.log('Add new item: ', newId);
      self.services.push({'id': newId, 'data': {
        'name': self.serviceName(), 'base_url': self.serviceBaseUrl()
      }});
    }else{
      console.log('Edit current item: ', self.editing.id);
      var indices = self.services().map(function(e, index) {
        return [e, index];
      }).filter(function(e) {
        return e[0].id == self.editing.id;
      });
      console.log('Index: ', indices[0][1])
      self.services.splice(indices[0][1], 1, {'id': self.editing.id, 'data': {
        'name': self.serviceName(), 'base_url': self.serviceBaseUrl()
      }});
    }
    self.dirtyCount(self.dirtyCount() + 1);
    self.clearModal();
  };

  self.submit = function() {
    console.log(logPrefix, 'submit', self.services());
    var service_list = self.services().map(function(item) {
      return item.data;
    });

    self.saveManager.save({'service_list': service_list})
        .then(function (data) {
          console.log(logPrefix, 'updated: ', data);
          self.dirtyCount(0);
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
      self.services(data.data.map(function(e, index) {
        return {'id': index, 'data': e};
      }));
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

$.extend(JupyterNodeSettings.prototype, ChangeMessageMixin.prototype);

var settings = new JupyterNodeSettings();
osfHelpers.applyBindings(settings, '#jupyterhubScope');
settings.loadConfig();
