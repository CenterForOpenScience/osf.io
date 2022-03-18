'use strict';

const $ = require('jquery');
const m = require('mithril');
const Fangorn = require('js/fangorn').Fangorn;
const Raven = require('raven-js');

const logPrefix = '[metadata] ';
const _ = require('js/rdmGettext')._;

const metadataFields = require('./metadata-fields.js');
const registrations = require('./registration.js');
const RegistrationSchemas = registrations.RegistrationSchemas;
const DraftRegistrations = registrations.DraftRegistrations;


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
  self.registrationSchemas = new RegistrationSchemas();
  self.draftRegistrations = new DraftRegistrations();
  self.registeringFilepath = null;
  self.selectDraftDialog = null;

  self.loadConfig = function() {
    if (self.loading !== null) {
      return;
    }
    self.loading = true;
    self.erad.load(self.baseUrl, function() {
      self.registrationSchemas.load(function() {
        self.draftRegistrations.load(function() {
          self.loadMetadata(self.baseUrl, function() {
            self.loading = false;
          });
        });
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

  self.lastMetadata = null;
  self.lastFields = null;
  self.currentSchemaId = null;

  self.createFields = function(schema, item, callback) {
    const fields = [];
    const itemData = item.data || {};
    (schema.pages || []).forEach(function(page) {
      (page.questions || []).forEach(function(question) {
        if (!question.qid || !question.qid.match(/^grdm-file:.+/)) {
          return;
        }
        const value = itemData[question.qid];
        const field = metadataFields.createField(
          self.erad,
          question,
          value,
          callback
        );
        fields.push({ field: field, question: question });
      });
    });
    return fields;
  };

  self.fieldsChanged = function() {
    if (!self.lastFields) {
      return;
    }
    self.lastFields.forEach(function(fieldSet) {
      const value = fieldSet.field.getValue(fieldSet.input);
      var error = null;
      try {
        metadataFields.validateField(
          self.erad,
          fieldSet.question,
          value
        );
      } catch(e) {
        error = e.message;
      }
      if (fieldSet.lastError == error) {
        return;
      }
      fieldSet.lastError = error;
      if (error) {
        fieldSet.errorContainer.text(error).show()
      } else {
        fieldSet.errorContainer.hide().text('')
      }
    });

  }

  self.prepareFields = function(container, schema) {
    const lastMetadataItems = (self.lastMetadata.items || []).filter(function(item) {
      return item.schema == schema.id;
    });
    const lastMetadataItem = lastMetadataItems[0] || {};
    container.empty();
    var fields = self.createFields(
      schema.attributes.schema,
      lastMetadataItem,
      self.fieldsChanged
    );
    self.lastFields = [];
    fields.forEach(function(fieldSet) {
      const errorContainer = $('<div></div>')
        .css('color', 'red').hide();
      const input = fieldSet.field.addElementTo(container, errorContainer);
      self.lastFields.push({
        field: fieldSet.field,
        question: fieldSet.question,
        input: input,
        lastError: null,
        errorContainer: errorContainer
      });
    });
    self.fieldsChanged();
  }

  self.findSchemaById = function(schemaId) {
    const targetSchemas = self.registrationSchemas.schemas.filter(function(s) {
      return s.id == schemaId;
    });
    if (targetSchemas.length == 0) {
      return null;
    }
    return targetSchemas[0];
  }

  self.editMetadata = function(filepath, item, dialog) {
    console.log(logPrefix, 'edit metadata: ', filepath, item);
    const currentMetadatas = self.projectMetadata.files.filter(function(f) {
      return f.path === filepath;
    });
    const currentMetadata = currentMetadatas[0] || null;
    if (!currentMetadata) {
      self.lastMetadata = {
        path: filepath,
        folder: item.kind === 'folder',
        items: [],
        registered: false
      };
    } else {
      self.lastMetadata = currentMetadata;
    }
    dialog.container.empty();
    const fieldContainer = $('<div></div>');
    const activeItems = (self.lastMetadata.items || []).filter(function(item) {
      return item.active;
    });
    const targetItem = activeItems[0] || {};
    const label = $('<label></label>').text(_('Data Schema:'));
    const schema = $('<select></select>');
    schema.append($('<option></option>')
      .attr('value', '')
      .text(_('Not selected')));
    (self.registrationSchemas.schemas || []).forEach(function(s) {
      schema.append($('<option></option>')
        .attr('value', s.id)
        .text(s.attributes.name));
    });
    if (targetItem.schema) {
      self.currentSchemaId = targetItem.schema;
      schema.val(self.currentSchemaId);
    }
    schema.change(function(event) {
      if (event.target.value == self.currentSchemaId) {
        return;
      }
      if (!event.target.value || !self.findSchemaById(event.target.value)) {
        self.currentSchemaId = null;
        self.lastFields = [];
        fieldContainer.empty();
        return;
      }
      self.currentSchemaId = event.target.value;
      self.prepareFields(
        fieldContainer,
        self.findSchemaById(self.currentSchemaId)
      );
    });
    const group = $('<div></div>').addClass('form-group')
      .append(label)
      .append(schema);
    dialog.container.append(group);
    if (targetItem.schema && self.findSchemaById(targetItem.schema)) {
      self.currentSchemaId = targetItem.schema;
      self.prepareFields(
        fieldContainer,
        self.findSchemaById(targetItem.schema)
      );
    }
    dialog.container.append(fieldContainer);
    dialog.dialog.modal('show');
  };

  self.deleteConfirmedModal = function() {
    const filepath = self.deleteConfirmingFilepath;
    self.deleteConfirmingFilepath = null;
    console.log(logPrefix, 'delete metadata: ', filepath);
    var url = self.baseUrl + 'files/' + filepath;
    return $.ajax({
        url: url,
        type: 'DELETE',
        dataType: 'json'
    }).done(function (data) {
      console.log(logPrefix, 'deleted: ', data);
      self.loadMetadata(self.baseUrl);
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

  self.extractProjectName = function(metadata) {
    if (!metadata) {
      return _('No name');
    }
    const projectNameJa = metadata['project-name-ja'];
    const projectNameEn = metadata['project-name-en'];
    const projectNameJaValue = projectNameJa ? (projectNameJa.value || null) : null;
    const projectNameEnValue = projectNameEn ? (projectNameEn.value || null) : null;
    if (!projectNameJaValue && !projectNameEnValue) {
      return _('No name');
    }
    if (projectNameJaValue && !projectNameEnValue) {
      return projectNameJaValue;
    }
    if (!projectNameJaValue && projectNameEnValue) {
      return projectNameEnValue;
    }
    return projectNameJaValue + ' / ' + projectNameEnValue;
  };

  self.createDraftsSelect = function() {
    const registrations = $('<select></select>');
    (self.draftRegistrations.registrations || []).forEach(function(r) {
      const projectName = self.extractProjectName(r.attributes.registration_metadata);
      registrations.append($('<option></option>')
        .attr('value', r.id)
        .text(r.id + ' - ' + projectName));
    });
    return registrations;
  }

  self.getFileMetadataPageURL = function(draftId) {
    const registrations = (self.draftRegistrations.registrations || []).filter(function(r) {
      return r.id == draftId;
    });
    if (registrations.length == 0) {
      console.error('No registrations', draftId);
      return null;
    }
    const registration = registrations[0];
    const schemaId = (((registration.relationships || {}).registration_schema || {}).data || {}).id;
    if (!schemaId) {
      console.error('No schemas for registration', draftId);
      return null;
    }
    const schema = self.findSchemaById(schemaId);
    if (!schema) {
      console.error('No schemas', schemaId);
      return null;
    }
    const pages = ((schema.attributes || {}).schema || {}).pages || [];
    const filePages = pages
      .map(function(page, pageIndex) {
        return {
          name: '' + (pageIndex + 1) + '-' + page.title,
          page: page
        };
      })
      .filter(function(page) {
        return (page.page.questions || []).filter(function(q) {
          return q.qid == 'grdm-files';
        }).length > 0;
      });
    if (filePages.length == 0) {
      console.error('No pages have grdm-files');
      return null;
    }
    const pageName = filePages[0].name;
    return '/registries/drafts/' + draftId + '/' + encodeURIComponent(pageName) + '?view_only=';
  };

  self.selectDraftModal = function() {
    const select = self.selectDraftDialog.container.find('select');
    const draftId = select.val();
    const filepath = self.registeringFilepath;
    if (!filepath) {
      const url = self.getFileMetadataPageURL(draftId);
      if (!url) {
        return;
      }
      window.open(url, '_blank');
      return;
    }
    self.registeringFilepath = null;
    console.log(logPrefix, 'register metadata: ', filepath, draftId);
    var url = self.baseUrl + 'draft_registrations/' + draftId + '/files/' + filepath;
    return $.ajax({
        url: url,
        type: 'PUT',
        dataType: 'json'
    }).done(function (data) {
      console.log(logPrefix, 'updated: ', data);
      self.selectDraftDialog.select
        .text(_('Open Registration'))
        .attr('data-dismiss', 'modal');
      self.draftRegistrations.load();
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
    self.deleteConfirmationDialog = self.initConfirmDeleteDialog();
    var dialog = self.initEditMetadataDialog();
    self.selectDraftDialog = self.initSelectDraftDialog();
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
            if (propname == 'itemButtons') {
              if (!self.projectMetadata) {
                return target[propname];
              }
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
                        self.editMetadata(filepath, item, dialog);
                      },
                      icon: 'fa fa-edit',
                      className : 'text-primary'
                  }, _('Edit Metadata'));
                  buttons.push(editButton);
                }
                if (currentMetadata) {
                  var registerButton = m.component(Fangorn.Components.button, {
                      onclick: function(event) {
                        self.registeringFilepath = filepath;
                        self.selectDraftDialog.select
                          .text(_('Select'))
                          .attr('data-dismiss', false);
                        self.selectDraftDialog.container.empty();
                        self.selectDraftDialog.container.append(self.createDraftsSelect());
                        self.selectDraftDialog.dialog.modal('show');
                      },
                      icon: 'fa fa-external-link',
                      className : 'text-success'
                  }, _('Register Metadata'));
                  buttons.push(registerButton)
                  var deleteButton = m.component(Fangorn.Components.button, {
                      onclick: function(event) {
                        self.deleteConfirmingFilepath = filepath;
                        self.deleteConfirmationDialog.modal('show');
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
            } else {
              return target[propname];
            }
          }
        });
      }
    });
  };

  self.saveModal = function() {
    const metadata = Object.assign({}, self.lastMetadata);
    metadata.items = (self.lastMetadata.items || [])
      .filter(function(item) {
        return item.schema != self.currentSchemaId;
      })
      .map(function(item) {
        return Object.assign({}, item, {
          active: false,
        });
      });
    if (self.currentSchemaId) {
      const metacontent = {
        schema: self.currentSchemaId,
        active: true,
        data: {},
      };
      self.lastFields.forEach(function(field) {
        metacontent.data[field.field.label] = {
          extra: [],
          comments: [],
          value: field.field.getValue(field.input),
        };
      });
      metadata.items.unshift(metacontent);
    }
    $.ajax({
      method: 'PATCH',
      url: self.baseUrl + 'files/' + metadata.path,
      contentType: 'application/json',
      data: JSON.stringify(metadata),
    }).done(function (data) {
      console.log(logPrefix, 'saved: ', data);
      self.loadMetadata(self.baseUrl)
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

  self.closeModal = function() {
    console.log(logPrefix, 'Modal closed');
    self.deleteConfirmingFilepath = null;
  };

  self.initEditMetadataDialog = function() {
    var close = $('<a href="#" class="btn btn-default" data-dismiss="modal"></a>').text(_('Close'));
    close.click(self.closeModal);
    var save = $('<a href="#" class="btn btn-success" data-dismiss="modal"></a>').text(_('Save'));
    save.click(self.saveModal);
    var container = $('<ul></ul>');
    var dialog = $('<div class="modal fade"></div>')
      .append($('<div class="modal-dialog modal-lg"></div>')
        .append($('<div class="modal-content"></div>')
          .append($('<div class="modal-header"></div>')
            .append($('<h3></h3>').text(_('Edit metadata'))))
          .append($('<form></form>')
            .append($('<div class="modal-body"></div>')
              .append($('<div class="row"></div>')
                .append($('<div class="col-sm-12"></div>')
                  .css('overflow-y', 'scroll')
                  .css('height', '80vh')
                  .append(container))))
            .append($('<div class="modal-footer"></div>')
              .append(close).append(save)))));
    dialog.appendTo($('#treeGrid'));
    return {dialog: dialog, container: container};
  };

  self.initConfirmDeleteDialog = function() {
    var close = $('<a href="#" class="btn btn-default" data-dismiss="modal"></a>').text(_('Close'));
    close.click(self.closeModal);
    var del = $('<a href="#" class="btn btn-success" data-dismiss="modal"></a>').text(_('Delete'));
    del.click(self.deleteConfirmedModal);
    var dialog = $('<div class="modal fade"></div>')
      .append($('<div class="modal-dialog modal-lg"></div>')
        .append($('<div class="modal-content"></div>')
          .append($('<div class="modal-header"></div>')
            .append($('<h3></h3>').text(_('Delete confirmation'))))
          .append($('<form></form>')
            .append($('<div class="modal-body"></div>')
              .append($('<div class="row"></div>')
                .append($('<div class="col-sm-12"></div>')
                  .append(_('Delete to confirm')))))
            .append($('<div class="modal-footer"></div>')
              .append(close).append(del)))));
    dialog.appendTo($('#treeGrid'));
    return dialog;
  };

  self.initSelectDraftDialog = function() {
    var close = $('<a href="#" class="btn btn-default" data-dismiss="modal"></a>').text(_('Close'));
    close.click(self.closeModal);
    var select = $('<a href="#" class="btn btn-success"></a>').text(_('Select'));
    select.click(self.selectDraftModal);
    var container = $('<ul></ul>');
    var dialog = $('<div class="modal fade"></div>')
      .append($('<div class="modal-dialog modal-lg"></div>')
        .append($('<div class="modal-content"></div>')
          .append($('<div class="modal-header"></div>')
            .append($('<h3></h3>').text(_('Select draft registration'))))
          .append($('<form></form>')
            .append($('<div class="modal-body"></div>')
              .append($('<div class="row"></div>')
                .append($('<div class="col-sm-12"></div>')
                  .append(container))))
            .append($('<div class="modal-footer"></div>')
              .append(close).append(select)))));
    dialog.appendTo($('#treeGrid'));
    return {dialog: dialog, container: container, select: select};
  };

}

var btn = new MetadataButtons();
btn.initFileTree();
