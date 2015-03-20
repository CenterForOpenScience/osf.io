'use strict';

var $osf = require('js/osfHelpers');
var ViewModel = require('js/citationsFolderPickerViewModel');

// Public API
function ZoteroNodeConfig(selector, url, folderPicker) {
    var self = this;
    self.url = url;
    self.folderPicker = folderPicker;
    self.viewModel = new ViewModel('zotero', url, selector, folderPicker);
    $osf.applyBindings(self.viewModel, selector);
}

module.exports = ZoteroNodeConfig;
