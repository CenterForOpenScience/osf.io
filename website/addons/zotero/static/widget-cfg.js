'use strict';

var $ = require('jquery');
var ko = require('knockout');
var $osf = require('osfHelpers');
var citations = require('../../../static/js/citations');
var CitationGrid = require('../../../static/js/citationGrid');

////////////////
// Public API //
////////////////

function CitationsWidget(gridSelector, styleSelector) {
    var apiUrl = window.contextVars.node.urls.api + 'zotero/citations/' + window.contextVars.zotero.folder_id + '/';
    this.grid = new CitationGrid('Zotero', gridSelector, styleSelector, apiUrl);
}

CitationsWidget.prototype.init = function() {
    var self = this;
    ko.applyBindings(self.viewModel, self.$element[0]);
};

// Skip if widget is not correctly configured
if ($('#zoteroWidget').length) {
    new CitationsWidget('#zoteroWidget', '#zoteroStyleSelect');
}
