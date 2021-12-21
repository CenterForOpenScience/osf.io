'use strict';

var ko = require('knockout');


function urljoin(url, path) {
  var r = url;
  var m = r.match(/^(.+)\/$/);
  if (m) {
    r = m[1];
  }
  if (!path.match(/^\/.*/)) {
    r += '/';
  }
  return r + path;
}

function BinderHubHostSettingsMixin() {
  var self = this;
  self.binderhubUrl = ko.observable('');
  self.binderhubOAuthClientId = ko.observable('');
  self.binderhubOAuthClientSecret = ko.observable('');
  self.jupyterhubUrl = ko.observable('');
  self.jupyterhubOAuthClientId = ko.observable('');
  self.jupyterhubOAuthClientSecret = ko.observable('');
  self.jupyterhubAdminAPIToken = ko.observable('');

  self.binderhubConfig = ko.computed(function() {
    if (!self.binderhubUrl()) {
      return null;
    }
    if (!self.binderhubOAuthClientId() || !self.binderhubOAuthClientSecret()) {
      return null;
    }
    if (!self.jupyterhubUrl()) {
      return null;
    }
    if (!self.jupyterhubOAuthClientId() || !self.jupyterhubOAuthClientSecret()) {
      return null;
    }
    if (!self.jupyterhubAdminAPIToken()) {
      return null;
    }
    if (self.binderhubUrlInvalid()) {
      return null;
    }
    if (self.jupyterhubUrlInvalid()) {
      return null;
    }
    return {
      binderhub_url: self.binderhubUrl(),
      binderhub_oauth_client_id: self.binderhubOAuthClientId(),
      binderhub_oauth_client_secret: self.binderhubOAuthClientSecret(),
      binderhub_oauth_authorize_url: urljoin(self.binderhubUrl(), '/api/oauth2/authorize'),
      binderhub_oauth_token_url: urljoin(self.binderhubUrl(), '/api/oauth2/token'),
      binderhub_oauth_scope: ['identity'],
      binderhub_services_url: urljoin(self.binderhubUrl(), '/api/services'),
      jupyterhub_url: self.jupyterhubUrl(),
      jupyterhub_oauth_client_id: self.jupyterhubOAuthClientId(),
      jupyterhub_oauth_client_secret: self.jupyterhubOAuthClientSecret(),
      jupyterhub_oauth_authorize_url: urljoin(self.jupyterhubUrl(), '/hub/api/oauth2/authorize'),
      jupyterhub_oauth_token_url: urljoin(self.jupyterhubUrl(), '/hub/api/oauth2/token'),
      jupyterhub_oauth_scope: ['identity'],
      jupyterhub_api_url: urljoin(self.jupyterhubUrl(), '/hub/api/'),
      jupyterhub_admin_api_token: self.jupyterhubAdminAPIToken(),
    }
  });

  self.binderhubUrlInvalid = ko.computed(function() {
    return self.binderhubUrl() && self.binderhubUrl().match('^https?\://.+') === null;
  });

  self.jupyterhubUrlInvalid = ko.computed(function() {
    return self.jupyterhubUrl() && self.jupyterhubUrl().match('^https?\://.+') === null;
  });

  self.hostCompleted = ko.computed(function() {
    return self.binderhubConfig() !== null;
  }, self);

  /** Reset all fields from binderhub host input modal */
  self.clearModal = function() {
      var self = this;
      self.binderhubUrl(null);
      self.binderhubOAuthClientId(null);
      self.binderhubOAuthClientSecret(null);
      self.jupyterhubUrl(null);
      self.jupyterhubOAuthClientId(null);
      self.jupyterhubOAuthClientSecret(null);
      self.jupyterhubAdminAPIToken(null);
  };
}

module.exports = BinderHubHostSettingsMixin;
