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

function toNumberOrNull(value) {
  if (!value) {
    return null;
  }
  if (!verifyNumberOrNull(value)) {
    return null;
  }
  return parseInt(value.trim());
}

function verifyNumberOrNull(value) {
  if (!value) {
    return true;
  }
  if (value.length === 0) {
    return true;
  }
  return value.match(/^\s*[0-9]+\s*$/) !== null;
}

function BinderHubHostSettingsMixin() {
  var self = this;
  self.binderhubUrl = ko.observable('');
  self.binderhubHasOAuthClient = ko.observable(false);
  self.binderhubOAuthClientId = ko.observable('');
  self.binderhubOAuthClientSecret = ko.observable('');
  self.jupyterhubUrl = ko.observable('');
  self.jupyterhubHasOAuthClient = ko.observable(false);
  self.jupyterhubOAuthClientId = ko.observable('');
  self.jupyterhubOAuthClientSecret = ko.observable('');
  self.jupyterhubAdminAPIToken = ko.observable('');
  self.jupyterhubMaxServers = ko.observable('');
  self.jupyterhubLogoutUrl = ko.observable('');

  self.binderhubOAuthClient = ko.computed(function() {
    if (!self.binderhubUrl()) {
      return null;
    }
    if (self.binderhubUrlInvalid()) {
      return null;
    }
    if (!self.binderhubHasOAuthClient()) {
      return {
        binderhub_url: self.binderhubUrl(),
        binderhub_oauth_client_id: null,
        binderhub_oauth_client_secret: null,
        binderhub_oauth_authorize_url: null,
        binderhub_oauth_token_url: null,
        binderhub_oauth_scope: null,
        binderhub_services_url: null,
      };
    }
    if (!self.binderhubOAuthClientId() || !self.binderhubOAuthClientSecret()) {
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
    };
  });

  self.jupyterhubOAuthClient = ko.computed(function() {
    if (!self.jupyterhubHasOAuthClient()) {
      // Use binderhubUrl as URL for JupyterHub
      if (!self.binderhubUrl()) {
        return null;
      }
      if (self.binderhubUrlInvalid()) {
        return null;
      }
      return {
        jupyterhub_url: self.binderhubUrl(),
        jupyterhub_oauth_client_id: null,
        jupyterhub_oauth_client_secret: null,
        jupyterhub_oauth_authorize_url: null,
        jupyterhub_oauth_token_url: null,
        jupyterhub_oauth_scope: null,
        jupyterhub_api_url: null,
        jupyterhub_admin_api_token: null,
        jupyterhub_max_servers: null,
        jupyterhub_logout_url: null,
      };
    }
    if (!self.jupyterhubUrl()) {
      return null;
    }
    if (self.jupyterhubUrlInvalid()) {
      return null;
    }
    if (!self.jupyterhubOAuthClientId() || !self.jupyterhubOAuthClientSecret()) {
      return null;
    }
    if (!self.jupyterhubAdminAPIToken()) {
      return null;
    }
    if (!verifyNumberOrNull(self.jupyterhubMaxServers())) {
      return null;
    }
    return {
      jupyterhub_url: self.jupyterhubUrl(),
      jupyterhub_oauth_client_id: self.jupyterhubOAuthClientId(),
      jupyterhub_oauth_client_secret: self.jupyterhubOAuthClientSecret(),
      jupyterhub_oauth_authorize_url: urljoin(self.jupyterhubUrl(), '/hub/api/oauth2/authorize'),
      jupyterhub_oauth_token_url: urljoin(self.jupyterhubUrl(), '/hub/api/oauth2/token'),
      jupyterhub_oauth_scope: ['identity'],
      jupyterhub_api_url: urljoin(self.jupyterhubUrl(), '/hub/api/'),
      jupyterhub_admin_api_token: self.jupyterhubAdminAPIToken(),
      jupyterhub_max_servers: toNumberOrNull(self.jupyterhubMaxServers()),
      jupyterhub_logout_url: self.jupyterhubLogoutUrl(),
    };
  });

  self.binderhubConfig = ko.computed(function() {
    var jhClient = self.jupyterhubOAuthClient();
    if (!jhClient) {
      return jhClient;
    }
    var bhClient = self.binderhubOAuthClient();
    if (!bhClient) {
      return bhClient;
    }
    return Object.assign({}, jhClient, bhClient);
  });

  self.binderhubUrlInvalid = ko.computed(function() {
    return self.binderhubUrl() && self.binderhubUrl().match('^https?\://.+') === null;
  });

  self.jupyterhubUrlInvalid = ko.computed(function() {
    return self.jupyterhubUrl() && self.jupyterhubUrl().match('^https?\://.+') === null;
  });

  self.jupyterhubMaxServersInvalid = ko.computed(function() {
    return !verifyNumberOrNull(self.jupyterhubMaxServers());
  });

  self.binderhubOAuthDisabled = ko.computed(function() {
    return !self.binderhubHasOAuthClient();
  }, self);

  self.jupyterhubOAuthDisabled = ko.computed(function() {
    return !self.jupyterhubHasOAuthClient();
  }, self);

  self.hostCompleted = ko.computed(function() {
    return self.binderhubConfig() !== null;
  }, self);

  /** Reset all fields from binderhub host input modal */
  self.clearModal = function() {
      var self = this;
      self.binderhubUrl(null);
      self.binderhubHasOAuthClient(false);
      self.binderhubOAuthClientId(null);
      self.binderhubOAuthClientSecret(null);
      self.jupyterhubUrl(null);
      self.jupyterhubHasOAuthClient(false);
      self.jupyterhubOAuthClientId(null);
      self.jupyterhubOAuthClientSecret(null);
      self.jupyterhubAdminAPIToken(null);
      self.jupyterhubMaxServers(null);
      self.jupyterhubLogoutUrl(null);
  };
}

module.exports = BinderHubHostSettingsMixin;
