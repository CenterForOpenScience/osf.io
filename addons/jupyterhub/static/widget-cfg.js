'use strict';

var $ = require('jquery');
var m = require('mithril');
var ko = require('knockout');
var Fangorn = require('js/fangorn').Fangorn;
var Raven = require('raven-js');
var osfHelpers = require('js/osfHelpers');

var logPrefix = '[jupyterhub] ';


function JupyterWidget() {
  var self = this;
  self.baseUrl = window.contextVars.node.urls.api + 'jupyterhub/';
  var services = undefined;
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

  self.initFileTree = function() {
    Fangorn.config = new Proxy(Fangorn.config, {
      get: function(targetprov, name) {
        var obj = targetprov[name];
        if (obj === undefined) {
          obj = {};
        }
        return new Proxy(obj, {
          get: function(target, propname) {
            if(propname == 'itemButtons') {
              return function(item) {
                if (services === undefined || item['kind'] != 'folder'
                    || item['data']['addonFullname'] !== undefined) {
                  return target[propname];
                }
                if (services.length == 0) {
                  return target[propname];
                }
                var base = Fangorn.Components.defaultItemButtons;
                if (target[propname] !== undefined) {
                  var prop = target[propname];
                  base = typeof prop === 'function' ? prop.apply(this, [item]) : prop;
                }
                var launcher = m.component(Fangorn.Components.button, {
                    onclick: function(event) {
                      console.log('[jupyter] launch: ', item, services);
                      var baseUrls = services.map(function(e) {
                        if (!e['base_url'].endsWith('/')) {
                          return e['base_url'] + '/';
                        }else{
                          return e['base_url'];
                        }
                      });
                      var data = item['data'];
                      var urls = baseUrls.map(function(baseUrl) {
                        return baseUrl + 'rcosrepo/import/' + data['nodeId'] +
                                '/' + data['provider'] + data['materialized'];
                      });
                      if (urls.length <= 1) {
                        window.open(urls[0], '_blank');
                      } else {
                        self.availableLinks(urls.map(function(url, index) {
                          return {'name': services[index]['name'], 'url': url};
                        }));
                        $('#jupyterSelectionDialog').modal('show');
                      }
                    },
                    icon: 'fa fa-external-link',
                    className : 'text-primary'
                }, 'JupyterHub');
                return {
                  view : function(ctrl, args, children) {
                    var tb = args.treebeard;
                    var mode = tb.toolbarMode;
                    return m('span', [
                               m.component(base, {treebeard : tb, mode : mode,
                                           item : item }),
                               launcher
                             ]);
                  }
                };
              };
            }else{
              return target[propname];
            }
          }
        });
      }
    });
  };
}

var w = new JupyterWidget();
osfHelpers.applyBindings(w, '#jupyterhubLinks');
w.initFileTree();
w.loadConfig();
