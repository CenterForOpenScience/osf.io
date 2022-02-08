'use strict';

var $ = require('jquery');
var m = require('mithril');
var Fangorn = require('js/fangorn').Fangorn;
var Raven = require('raven-js');

var logPrefix = '[metadata] ';
var _ = require('js/rdmGettext')._;

var metadataFields = require('./MetadataFields.js');


function ERad() {
  var self = this;

  self.candidates = null;

  self.load = function(baseUrl, callback) {
    var url = baseUrl + 'erad/candidates';
    console.log(logPrefix, 'loading: ', url);

    return $.ajax({
        url: url,
        type: 'GET',
        dataType: 'json'
    }).done(function (data) {
      console.log(logPrefix, 'loaded: ', data);
      self.candidates = ((data.data || {}).attributes || {}).records;
      callback();
    }).fail(function(xhr, status, error) {
      Raven.captureMessage('Error while retrieving addon info', {
          extra: {
              url: url,
              status: status,
              error: error
          }
      });
      callback();
    });
  };
}


function MetadataButtons() {
  var self = this;
  self.baseUrl = window.contextVars.node.urls.api + 'metadata/';
  self.loading = null;
  self.projectMetadata = null;
  self.erad = new ERad();

  self.loadConfig = function() {
    if (self.loading !== null) {
      return;
    }
    self.loading = true;
    self.erad.load(self.baseUrl, function() {
      self.loadMetadata(self.baseUrl, function() {
        self.loading = false;
      });
    });
  };

  self.loadMetadata = function(baseUrl, callback) {
    var url = baseUrl + 'project';
    console.log(logPrefix, 'loading: ', url);

    return $.ajax({
        url: url,
        type: 'GET',
        dataType: 'json'
    }).done(function (data) {
      console.log(logPrefix, 'loaded: ', data);
      self.projectMetadata = (data.data || {}).attributes;
      callback();
    }).fail(function(xhr, status, error) {
      Raven.captureMessage('Error while retrieving addon info', {
          extra: {
              url: url,
              status: status,
              error: error
          }
      });
      callback();
    });
  };

  self.lastMetadata = null;
  self.lastFields = null;

  self.getFields = function() {
    return [
      // TBD Registration Schemaに基づいて決定
      new metadataFields.ERadResearcherNumberField(self.erad, 'e-Rad Researcher Number'),
      new metadataFields.ERadResearcherNameField(self.erad, 'e-Rad Researcher Name(ja)', 'ja'),
      new metadataFields.ERadResearcherNameField(self.erad, 'e-Rad Researcher Name(en)', 'en'),
    ];
  };

  self.initFileTree = function() {
    var dialog = self.initDialog();
    // Request to load config
    self.loadConfig();

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
                /*if (item['kind'] != 'folder' || item['data']['addonFullname'] !== undefined) {
                  return target[propname];
                }*/
                var base = Fangorn.Components.defaultItemButtons;
                if (target[propname] !== undefined) {
                  var prop = target[propname];
                  var baseButtons = typeof prop === 'function' ? prop.apply(this, [item]) : prop;
                  if (baseButtons !== undefined) {
                    base = baseButtons;
                  }
                }
                var filepath = item.data.provider + (item.data.materialized || '/');
                var currentMetadatas = self.projectMetadata.files.filter(function(f) {
                  return f.path === filepath;
                });
                var currentMetadata = currentMetadatas[0] || null;
                var parentMetadatas = self.projectMetadata.files.filter(function(f) {
                  return f.path !== filepath && filepath.startsWith(f.path);
                });
                var parentMetadata = parentMetadatas[0] || null;
                var buttons = [];
                if (!parentMetadata) {
                  var editButton = m.component(Fangorn.Components.button, {
                      onclick: function(event) {
                        console.log(logPrefix, 'edit metadata: ', filepath, item);
                        if (!currentMetadata) {
                          self.lastMetadata = {
                            path: filepath,
                            folder: item.kind === 'folder',
                            items: [],
                            registered: false,
                          };
                        } else {
                          self.lastMetadata = currentMetadata;
                        }
                        dialog.container.empty();
                        var fields = self.getFields();
                        self.lastFields = [];
                        fields.forEach(function(field) {
                          var input = field.addElementTo(dialog.container);
                          self.lastFields.push({
                            field: field,
                            input: input,
                          });
                        });
                        dialog.dialog.modal('show');
                      },
                      icon: 'fa fa-edit',
                      className : 'text-primary'
                  }, _('Edit Metadata'));
                  buttons.push(editButton);
                }
                if (currentMetadata) {
                  var registerButton = m.component(Fangorn.Components.button, {
                      onclick: function(event) {
                        console.log(logPrefix, 'register metadata: ', item);
                        /*dialog.container.empty();
                        var fields = self.getFields();
                        fields.forEach(function(field) {
                            field.addElementTo(dialog.container);
                        });
                        dialog.dialog.modal('show');*/
                        // TBD: Metadataタブを開き、指定されたファイルのregisteredプロパティをTrueにして登録
                      },
                      icon: 'fa fa-external-link',
                      className : 'text-success'
                  }, _('Register Metadata'));
                  buttons.push(registerButton)
                  var deleteButton = m.component(Fangorn.Components.button, {
                      onclick: function(event) {
                        console.log(logPrefix, 'delete metadata: ', item);
                        // TBD
                      },
                      icon: 'fa fa-trash',
                      className : 'text-danger'
                  }, _('Delete Metadata'));
                  buttons.push(deleteButton)
                }
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
                             ].concat(buttons));
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

  self.saveModal = function(callback) {
    // TBD
    const metadata = Object.assign({}, self.lastMetadata);
    metadata.items = self.lastFields.map(function(field) {
      return {
        name: field.field.label,
        value: field.input.val(),
      };
    });
    $.ajax({
      method: 'PATCH',
      url: self.baseUrl + 'files/' + metadata.path,
      contentType: 'application/json',
      data: JSON.stringify(metadata),
    }).done(function (data) {
      console.log(logPrefix, 'saved: ', data);
      self.loadMetadata(self.baseUrl, function() {
        if (!callback) {
          return;
        }
        callback();
      })
    }).fail(function(xhr, status, error) {
      Raven.captureMessage('Error while retrieving addon info', {
          extra: {
              url: url,
              status: status,
              error: error
          }
      });
      if (callback) {
        callback();
      }
    });
  };

  self.closeModal = function() {
    console.log('Modal closed');
  };

  self.initDialog = function() {
    var close = $('<a href="#" class="btn btn-default" data-dismiss="modal">Close</a>');
    close.click(self.closeModal);
    var save = $('<a href="#" class="btn btn-success" data-dismiss="modal">Save</a>');
    save.click(self.saveModal);
    var container = $('<ul></ul>');
    var dialog = $('<div class="modal fade"></div>')
      .append($('<div class="modal-dialog modal-lg"></div>')
        .append($('<div class="modal-content"></div>')
          .append('<div class="modal-header"><h3>Metadata</h3></div>')
          .append($('<form></form>')
            .append($('<div class="modal-body"></div>')
              .append($('<div class="row"></div>')
                .append($('<div class="col-sm-12"></div>')
                  .append(container))))
            .append($('<div class="modal-footer"></div>')
              .append(close).append(save)))));
    dialog.appendTo($('#treeGrid'));
    return {dialog: dialog, container: container};
  };

}

var btn = new MetadataButtons();
btn.initFileTree();
