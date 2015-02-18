'use strict';

var $ = require('jquery');
var ko = require('knockout');
var $osf = require('osfHelpers');
var citations = require('../../../static/js/citations');
var CitationGrid = require('../../../static/js/citationGrid');

require('./citations_widget.css');

////////////////
// Public API //
////////////////

function CitationsWidget(gridSelector, styleSelector) {
    var apiUrl = window.contextVars.node.urls.api + 'mendeley/citations/';
    this.grid = new CitationGrid('Mendeley', gridSelector, styleSelector, apiUrl);
}

CitationsWidget.prototype.init = function() {
    var self = this;
    ko.applyBindings(self.viewModel, self.$element[0]);
};
//module.exports = MendeleySettings;
new CitationsWidget('#mendeleyWidget', '#mendeleyStyleSelect');
