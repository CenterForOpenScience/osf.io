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
    var apiUrl = window.contextVars.node.urls.api + 'mendeley/citations/' + window.contextVars.mendeley.folder_id + '/';
    this.grid = new CitationGrid('Mendeley', gridSelector, styleSelector, apiUrl);
}

CitationsWidget.prototype.init = function() {
    var self = this;
    ko.applyBindings(self.viewModel, self.$element[0]);
};

// Skip if widget is not correctly configured
if ($('#mendeleyWidget').length) {
    new CitationsWidget('#mendeleyWidget', '#mendeleyStyleSelect');
}
