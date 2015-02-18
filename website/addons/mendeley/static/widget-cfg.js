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

function CitationsWidget(selector) {   
    var url = window.contextVars.node.urls.api + 'mendeley/citations/';
    this.grid = new CitationGrid(selector, url);
}

CitationsWidget.prototype.init = function() {
    var self = this;
    ko.applyBindings(self.viewModel, self.$element[0]);
};
//module.exports = MendeleySettings;
new CitationsWidget('#mendeleyWidget');
