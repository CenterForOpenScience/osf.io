'use strict';

var $ = require('jquery');
var $osf = require('js/osfHelpers');
var Raven = require('raven-js');

var logPrefix = '[metadata] ';

function RegistrationSchemas() {
  var self = this;

  self.schemas = [];

  self.load = function(callback, nextUrl) {
    const params = new URLSearchParams({page: 1});
    const url = nextUrl || ($osf.apiV2Url('schemas/registrations/') + '?' + params);
    $osf.ajaxJSON(
      'GET',
      url,
      {
        'isCors': true,
        'fields': {
          xhrFields: {withCredentials: true}
        }
      }
    ).done(function (data) {
      Array.prototype.push.apply(self.schemas, self.getSchemaWithFile(data.data || []));
      if (data.links.next) {
        self.load(callback, data.links.next);
        return;
      }
      console.log(logPrefix, 'schemas: ', self.schemas);
      if (!callback) {
        return;
      }
      callback();
    }).fail(function(xhr, status, error) {
      Raven.captureMessage('Error while retrieving addon info', {
          extra: {
              url: url,
              status: status,
              error: error
          }
      });
      if (!callback) {
        return;
      }
      callback();
    });
  };

  self.getSchemaWithFile = function(data) {
    return data.filter(function(elem) {
      if (!elem.attributes || !elem.attributes.schema || !elem.attributes.schema.pages) {
        return false;
      }
      var matched = elem.attributes.schema.pages.filter(function(page) {
        if (!page.questions) {
          return false;
        }
        var questions = page.questions.filter(function(q) {
          return q.qid.match(/^grdm-file:/);
        });
        return questions.length > 0;
      });
      return matched.length > 0;
    });
  };
}


function DraftRegistrations() {
  var self = this;

  self.registrations = [];

  self.load = function(callback) {
    const params = new URLSearchParams({
      'page[size]': 100,
      'embed[]': 'initiator',
      'embed[]': 'branched_from',
      page: 1
    });
    const node = window.contextVars.node;
    const url = $osf.apiV2Url('nodes/' + node.id + '/draft_registrations/') + '?' + params;
    $osf.ajaxJSON(
      'GET',
      url,
      {
        'isCors': true,
        'fields': {
          xhrFields: {withCredentials: true}
        }
      }
    ).done(function (data) {
      self.registrations = [];
      (data.data || []).forEach(function(reg) {
        self.registrations.push(reg);
      });
      console.log(logPrefix, 'registrations: ', self.registrations);
      if (!callback) {
        return;
      }
      callback();
    }).fail(function(xhr, status, error) {
      Raven.captureMessage('Error while retrieving addon info', {
          extra: {
              url: url,
              status: status,
              error: error
          }
      });
      if (!callback) {
        return;
      }
      callback();
    });
  };

}


module.exports = {
  RegistrationSchemas: RegistrationSchemas,
  DraftRegistrations: DraftRegistrations,
};
