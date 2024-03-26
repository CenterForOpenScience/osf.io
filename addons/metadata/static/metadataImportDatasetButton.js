'use strict';

const $ = require('jquery');
const m = require('mithril');
const Fangorn = require('js/fangorn').Fangorn;

const $osf = require('js/osfHelpers');

const logPrefix = '[metadata] ';
const _ = require('js/rdmGettext')._;


function ImportDatasetButton(treebeard, item, tempIdProvider) {
  const self = this;
  self.treebeard = treebeard;
  self.item = item;
  self.progressApiUrl = null;
  self.progressItems = null;
  self.tempIdProvider = tempIdProvider;

  self.showDialog = function(callback) {
    const dialog = $('<div class="modal fade" data-backdrop="static"></div>');
    const close = $('<a href="#" class="btn btn-default" data-dismiss="modal"></a>').text(_('Close'));
    const perform = $('<a href="#" class="btn btn-success"></a>')
      .text(_('Import Dataset')).attr('disabled', 'disabled');
    const textChange = function(event) {
      const value = importURL.val();
      if (!value || value.trim().length === 0) {
        perform.attr('disabled', 'disabled');
        return;
      }
      perform.attr('disabled', null);
      if (event.key === 'Enter') {
        importProcess();
        return;
      }
    };
    const importURL = $('<input type="text" class="form-control">')
      .on('keyup', textChange)
      .on('change', textChange)
      .attr('placeholder', _('Enter URL to import dataset'));
    const importProcess = function() {
      const progressIcon = $('<i class="fa fa-spinner fa-spin"></i>');
      perform.text(_('Importing...')).prepend(progressIcon);
      callback(importURL.val().trim(), function(files, error) {
        if (error !== null) {
          console.error(logPrefix, 'Error importing dataset:', error);
          $osf.growl('Error', _('Error importing dataset: ') + error.message);
          dialog.modal('hide');
          return;
        }
        dialog.modal('hide');
      });
    };
    perform.on('click', importProcess);
    const title = $('<h3></h3>').text(_('Import Dataset'));
    const body = $('<div></div>')
      .append($('<p></p>').text(_('Enter the URL of the dataset you would like to import.')))
      .append(importURL);
    const footer = $('<div class="modal-footer"></div>')
      .append(close)
      .append(perform);
    dialog
      .append($('<div class="modal-dialog modal-lg"></div>')
        .append($('<div class="modal-content"></div>')
          .append($('<div class="modal-header"></div>').append(title))
          .append($('<div class="modal-body"></div>').append(body))
          .append(footer)
        ));
    dialog.appendTo($('#treeGrid'));
    dialog.modal('show');
  };

  self.openFolder = function() {
    if (self.item.open) {
      return;
    }
    const index = self.treebeard.returnIndex(self.item.id);
    self.treebeard.toggleFolder(index);
  }

  self.updateProgress = function(progress) {
    if (!progress.info || !progress.info.filenames) {
      return false;
    }
    var created = false;
    if (self.progressItems === null) {
      self.openFolder();
      const items = [];
      progress.info.filenames.forEach(function(filename) {
        const blankItem = {       // create a blank item that will refill when upload is finished.
          name: 'Downloading...',
          kind: 'file',
          provider: self.item.data.provider,
          children: [],
          permissions: {
              view: false,
              edit: false
          },
          tmpID: self.tempIdProvider.assign(),
          progress: 0,
          uploadState : function() {
            return 'downloading'
          },
        };
        const newItem = self.treebeard.createItem(blankItem, self.item.id);
        newItem.inProgress = true;
        items.push(newItem);
      });
      self.treebeard.redraw();
      self.progressItems = items;
      created = true;
    }
    var changed = false;
    progress.info.filenames.forEach(function(filename, index) {
      if (filename.filename === null) {
        return;
      }
      const item = self.progressItems[index];
      if (!item.inProgress) {
        return;
      }
      item.inProgress = false;
      item.data.name = filename.filename;
      item.data.progress = 100;
      item.notify.update(_('Downloaded!'), 'success', undefined, 1000);
      item.data.uploadState = null;
      changed = true;
    });
    if (changed) {
      self.treebeard.redraw();
    }
    return created;
  };

  self.checkProgress = function(callback) {
    if (!self.progressApiUrl) {
      throw new Error('progressApiUrl is not set');
    }
    console.log(logPrefix, 'checking progress...');
    $.ajax({
      url: self.progressApiUrl,
      type: 'GET',
      dataType: 'json'
    }).done(function(response) {
      console.log(logPrefix, 'progress:', response);
      if (response.state === 'SUCCESS') {
        console.log(logPrefix, 'done');
        self.progressApiUrl = null;
        self.progressItems = null;
        self.treebeard.updateFolder(null, self.item);
        if (callback) {
          callback(response.info.filenames, null);
        }
        return;
      }
      if (response.error) {
        if (callback) {
          callback(null, {
            message: response.error
          });
        } else {
          console.error(logPrefix, 'error:', response.error);
          $osf.growl('Error', _('Error importing dataset: ') + response.error);
        }
        self.progressApiUrl = null;
        self.progressItems = null;
        self.treebeard.updateFolder(null, self.item);
        return;
      }
      const created = self.updateProgress(response);
      if (created) {
        if (callback) {
          callback(response.info.filenames, null);
        }
        setTimeout(function() {
          self.checkProgress();
        }, 500);
        return;
      }
      setTimeout(function() {
        self.checkProgress(callback);
      }, 500);
    }).fail(function(xhr, textStatus, error) {
      console.error(logPrefix, 'error:', textStatus, error);
      if (callback) {
        callback(null, error);
      } else {
        $osf.growl('Error', _('Error importing dataset: ') + error.message);
      }
      self.progressApiUrl = null;
      self.progressItems = null;
      self.treebeard.updateFolder(null, self.item);
    });
  };

  self.perform = function(importURL, callback) {
    var url = contextVars.node.urls.api;
    if (!url.match(/.*\/$/)) {
        url += '/';
    }
    url += 'metadata/dataset/providers/' + self.item.data.provider + '/folders' + self.item.data.path;
    const params = {
      url: importURL
    };
    return $osf.putJSON(url, params).done(function (data) {
      self.progressApiUrl = data.progress_api_url;
      setTimeout(function() {
        self.checkProgress(callback);
      }, 500);

    }).fail(function(xhr, status, error) {
      callback(null, error);
      Raven.captureMessage('Error while depositing file', {
        extra: {
            url: url,
            status: status,
            error: error
        }
      });
    });
  };

  self.createButton = function() {
    const button = m.component(Fangorn.Components.button, {
      onclick: function(event) {
        self.showDialog(function(importURL, callback) {
          console.log(logPrefix, 'importURL', importURL);
          self.perform(importURL, callback);
        });
      },
      icon: 'fa fa-plus',
      className : 'text-success'
    }, _('Import Dataset'));
    return button;
  };
}

module.exports = ImportDatasetButton;
