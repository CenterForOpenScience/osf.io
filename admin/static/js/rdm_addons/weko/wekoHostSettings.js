'use strict';

var ko = require('knockout');

function WEKOHostSettingsMixin() {
  var self = this;
  self.wekoName = ko.observable('');
  self.wekoUrl = ko.observable('');
  self.wekoOAuthClientId = ko.observable('');
  self.wekoOAuthClientSecret = ko.observable('');

  self.wekoOAuthClient = ko.computed(function() {
    if (!self.wekoUrl()) {
      return null;
    }
    if (self.wekoUrlInvalid()) {
      return null;
    }
    if (!self.wekoOAuthClientId() || !self.wekoOAuthClientSecret()) {
      return null;
    }
    return {
      display_name: self.wekoName() || self.wekoUrl(),
      url: self.wekoUrl(),
      oauth_client_id: self.wekoOAuthClientId(),
      oauth_client_secret: self.wekoOAuthClientSecret(),
    };
  });

  self.wekoConfig = ko.computed(function() {
    return self.wekoOAuthClient();
  });

  self.wekoUrlInvalid = ko.computed(function() {
    return self.wekoUrl() && self.wekoUrl().match('^https?\://.+') === null;
  });

  self.hostCompleted = ko.computed(function() {
    return self.wekoConfig() !== null;
  }, self);

  /** Reset all fields from binderhub host input modal */
  self.clearModal = function() {
      var self = this;
      self.wekoName(null);
      self.wekoUrl(null);
      self.wekoOAuthClientId(null);
      self.wekoOAuthClientSecret(null);
  };
}

module.exports = WEKOHostSettingsMixin;
