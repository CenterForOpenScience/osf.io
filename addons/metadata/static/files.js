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

  self.loadConfig = function(callback) {
    if (self.loading !== null) {
      return;
    }
    self.loading = true;
    self.erad.load(self.baseUrl, function() {
      self.registrationSchemas.load(function() {
        self.loadMetadata(self.baseUrl, function() {
          self.loading = false;
          const path = self.processHash();
          if (!callback) {
            return;
          }
          callback(path);
        });
      });
    });
  };

  self.processHash = function() {
    const path = self.getContextPath();
    if (!path) {
      return null;
    }
    if (window.location.hash !== '#edit-metadata') {
      return path;
    }
    self.editMetadata(path, null);
    return path;
  }

  self.getContextPath = function() {
    if (contextVars.file && contextVars.file.provider) {
      return contextVars.file.provider + contextVars.file.materializedPath;
    }
    if (!self.projectMetadata) {
      return null;
    }
    const currentMetadata = (self.projectMetadata.files || []).filter(function(f) {
      return f.urlpath === window.location.pathname;
    })[0];
    if (!currentMetadata) {
      return null;
    }
    return currentMetadata.path;
  }

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

  self.editMetadata = function(filepath, item) {
    const dialog = self.editMetadataDialog;
    console.log(logPrefix, 'edit metadata: ', filepath, item);
    const currentMetadatas = self.projectMetadata.files.filter(function(f) {
      return f.path === filepath;
    });
    const currentMetadata = currentMetadatas[0] || null;
    if (!currentMetadata) {
      self.lastMetadata = {
        path: filepath,
        folder: item === null ? false : item.kind === 'folder',
        items: [],
      };
    } else {
      self.lastMetadata = currentMetadata;
    }
    dialog.container.empty();
    const fieldContainer = $('<div></div>');
    const activeItems = (self.lastMetadata.items || []).filter(function(item_) {
      return item_.active;
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

  self.includePathInDraftRegistration = function(path, registration) {
    if (!registration.attributes) {
      return false;
    }
    if (!registration.attributes.registration_metadata) {
      return false;
    }
    const files = registration.attributes.registration_metadata['grdm-files'];
    if (!files) {
      return false;
    }
    if (!files.value) {
      return false;
    }
    const fileEntries = JSON.parse(files.value);
    return fileEntries.filter(function(file) {
      return file.path == path;
    }).length > 0;
  };

  self.createDraftsSelect = function() {
    const registrations = $('<ul></ul>').css('list-style-type', 'none');
    (self.draftRegistrations.registrations || []).forEach(function(r) {
      const projectName = self.extractProjectName(r.attributes.registration_metadata);
      registrations.append($('<li></li>')
        .append($('<input></input>')
          .css('margin-right', '0.5em')
          .attr('type', 'checkbox')
          .attr('id', 'draft-' + r.id)
          .attr('name', 'draft-' + r.id)
          .attr('checked', self.includePathInDraftRegistration(self.registeringFilepath, r)))
        .append($('<label></label>')
          .css('margin-right', '0.5em')
          .attr('for', 'draft-' + r.id)
          .text(projectName + ' - ' + r.id))
        .append($('<span></span>')
          .attr('id', 'draft-' + r.id + '-link')));
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

  self.openDraftModal = function() {
    const draftSelection = $('<div></div>').text(_('Loading...'));
    self.selectDraftDialog.select
      .text(_('Select'))
      .attr('data-dismiss', false);
    self.selectDraftDialog.container.empty();
    self.selectDraftDialog.container.append(draftSelection);
    self.selectDraftDialog.dialog.modal('show');
    self.draftRegistrations.load(function() {
      draftSelection.empty();
      draftSelection.append(self.createDraftsSelect());
    });
  };

  self.updateRegistrationAsync = function(checked, filepath, draftId, link) {
    return new Promise(function(resolve, perror) {
      console.log(logPrefix, 'register metadata: ', filepath, draftId);
      var url = self.baseUrl + 'draft_registrations/' + draftId + '/files/' + filepath;
      link.text(checked ? _('Registering...') : _('Deleting...'));
      return $.ajax({
          url: url,
          type: checked ? 'PUT' : 'DELETE',
          dataType: 'json'
      }).done(function (data) {
        link.empty();
        link.append($('<a></a>')
          .text(_('Open'))
          .attr('href', self.getFileMetadataPageURL(draftId)));
        resolve(data);
      }).fail(function(xhr, status, error) {
        perror(url, xhr, status, error);
      });
    });
  }

  self.selectDraftModal = function() {
    const filepath = self.registeringFilepath;
    if (!filepath) {
      return;
    }
    self.registeringFilepath = null;
    const ops = [];
    (self.draftRegistrations.registrations || []).forEach(function(r) {
      const checkbox = self.selectDraftDialog.container.find('#draft-' + r.id);
      const checked = checkbox.is(':checked');
      const oldChecked = self.includePathInDraftRegistration(filepath, r);
      if (checked == oldChecked) {
        return;
      }
      const link = self.selectDraftDialog.container.find('#draft-' + r.id + '-link');
      ops.push(self.updateRegistrationAsync(checked, filepath, r.id, link));
    });
    Promise.all(ops)
      .then(function(data) {
        console.log(logPrefix, 'updated: ', data);
        self.selectDraftDialog.select
          .text(_('Close'))
          .attr('data-dismiss', 'modal');
        self.draftRegistrations.load();
      })
      .catch(function(url, xhr, status, error) {
        Raven.captureMessage('Error while retrieving addon info', {
            extra: {
                url: url,
                status: status,
                error: error
            }
        });
      });
  };

  self.createFangornButtons = function(filepath, item) {
    return self.createButtonsBase(
      filepath,
      item,
      function(options, label) {
        return m.component(Fangorn.Components.button, options, label);
      }
    );
  }

  self.createButtonsBase = function(filepath, item, createButton) {
    const currentMetadatas = self.projectMetadata.files.filter(function(f) {
      return f.path === filepath;
    });
    const currentMetadata = currentMetadatas[0] || null;
    const parentMetadatas = self.projectMetadata.files.filter(function(f) {
      return f.path !== filepath && filepath.startsWith(f.path);
    });
    const parentMetadata = parentMetadatas[0] || null;
    const buttons = [];
    if (!parentMetadata) {
      const editButton = createButton({
        onclick: function(event) {
          self.editMetadata(filepath, item);
        },
        icon: 'fa fa-edit',
        className : 'text-primary'
      }, _('Edit Metadata'));
      buttons.push(editButton);
    }
    if (currentMetadata) {
      const registerButton = createButton({
        onclick: function(event) {
          self.registeringFilepath = filepath;
          self.openDraftModal();
        },
        icon: 'fa fa-external-link',
        className : 'text-success'
      }, _('Register Metadata'));
      buttons.push(registerButton)
      const deleteButton = createButton({
        onclick: function(event) {
          self.deleteConfirmingFilepath = filepath;
          self.deleteConfirmationDialog.modal('show');
        },
        icon: 'fa fa-trash',
        className : 'text-danger'
      }, _('Delete Metadata'));
      buttons.push(deleteButton)
    }
    return buttons;
  }

  self.initBase = function(callback) {
    self.deleteConfirmationDialog = self.initConfirmDeleteDialog();
    self.editMetadataDialog = self.initEditMetadataDialog();
    self.selectDraftDialog = self.initSelectDraftDialog();
    // Request to load config
    self.loadConfig(callback);
  }

  self.initFileView = function() {
    self.initBase(function(path) {
      if (!path) {
        return;
      }
      const buttons = $('<div></div>')
        .addClass('btn-group m-t-xs')
        .attr('id', 'metadata-toolbar');
      self.createButtonsBase(
        path,
        null,
        function(options, label) {
          const btn = $('<button></button>')
            .addClass('btn')
            .addClass('btn-sm');
          if (options.className) {
            btn.addClass(options.className.replace(/^text-/, 'btn-'));
          }
          if (options.icon) {
            btn.append($('<i></i>').addClass(options.icon));
          }
          if (options.onclick) {
            btn.click(options.onclick);
          }
          btn.append($('<span></span>').text(label));
          return btn;
        }
      )
        .forEach(function(button) {
          buttons.append(button);
        });
      $('.btn-toolbar').prepend(buttons);
    });
  }

  self.initFileTree = function() {
    self.initBase();

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
                const buttons = self.createFangornButtons(filepath, item);
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
    const url = self.baseUrl + 'files/' + metadata.path;
    $.ajax({
      method: 'PATCH',
      url: url,
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
            .append($('<h3></h3>').text(_('Edit Metadata'))))
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
            .append($('<h3></h3>').text(_('Delete Metadata'))))
          .append($('<form></form>')
            .append($('<div class="modal-body"></div>')
              .append($('<div class="row"></div>')
                .append($('<div class="col-sm-12"></div>')
                  .append(_('Do you want to delete metadata? This operation cannot be undone.')))))
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

if (contextVars.metadataAddonEnabled) {
  var btn = new MetadataButtons();
  if ($('#fileViewPanelLeft').length > 0) {
    // File View
    btn.initFileView();
  } else {
    btn.initFileTree();
  }
}
