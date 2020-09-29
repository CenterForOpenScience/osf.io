'use strict';

var $ = require('jquery');
var m = require('mithril');
var Fangorn = require('js/fangorn').Fangorn;
var Raven = require('raven-js');

var logPrefix = '[jupyterhub] ';


function JupyterButton() {
  var self = this;
  self.baseUrl = window.contextVars.node.urls.api + 'jupyterhub/';
  var services = undefined;

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

  self.initFileTree = function() {
    var dialog = self.initSelectionDialog();
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
                      console.log(logPrefix, 'launch: ', item, services);
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
                        dialog.container.empty();
                        urls.forEach(function(url, index) {
                          var a = $('<a target="_blank"></a>')
                            .text(services[index]['name'])
                            .attr('href', url);
                          dialog.container.append($('<li></li>').append(a));
                        });
                        dialog.dialog.modal('show');
                      }
                    },
                    icon: 'fa fa-external-link',
                    className : 'text-primary'
                }, 'Launch');
                return {
                  view : function(ctrl, args, children) {
                    var tb = args.treebeard;
                    var mode = tb.toolbarMode;
                    if (tb.options.placement === 'fileview') {
                      return m('span', []);
                    }
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

  self.closeModal = function() {
    console.log('Modal closed');
  };

  self.initSelectionDialog = function() {
    var close = $('<a href="#" class="btn btn-default" data-dismiss="modal">Close</a>');
    close.click(self.closeModal);
    var container = $('<ul></ul>');
    var dialog = $('<div class="modal fade"></div>')
      .append($('<div class="modal-dialog modal-lg"></div>')
        .append($('<div class="modal-content"></div>')
          .append('<div class="modal-header"><h3>Select JupyterHub</h3></div>')
          .append($('<form></form>')
            .append($('<div class="modal-body"></div>')
              .append($('<div class="row"></div>')
                .append($('<div class="col-sm-6"></div>')
                  .append(container))))
            .append($('<div class="modal-footer"></div>')
              .append(close)))));
    dialog.appendTo($('#treeGrid'));
    return {dialog: dialog, container: container};
  };

}

var btn = new JupyterButton();
btn.initFileTree();
btn.loadConfig();
