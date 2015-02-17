'use strict';

var $ = require('jquery');
var ko = require('knockout');
var $osf = require('osfHelpers');
var citations = require('../../../static/js/citations');
var CitationGrid = require('../../../static/js/citationGrid');

require('./citations_widget.css');

// var CitationsWidgetViewModel = function() {
//     var self = this;

//     self.citationsApiUrl = window.contextVars.node.urls.api + 'mendeley/citations/';

//     self.error = ko.observable();
//     self.name = ko.observable();
//     self.citations = ko.observableArray();

//     self.updateList = function() {
//         var styleRequest = $.get('/static/vendor/bower_components/styles/apa.csl');
//         var citationsRequest = $.get(self.citationsApiUrl);
//         $.when(styleRequest, citationsRequest).done(function(style, data) {
//             var citeproc = citations.makeCiteproc(style[0], data[0], 'text');
//             var bibliography = citeproc.makeBibliography();
//             self.citations(bibliography[1]);
//         }).fail(function() {
//            self.error('Could not load citations');
//         });
//     };

//     self.updateList();
// };


////////////////
// Public API //
////////////////

function CitationsWidget(gridSelector, styleSelector) {
    var apiUrl = window.contextVars.node.urls.api + 'mendeley/citations/';
    this.grid = new CitationGrid(gridSelector, styleSelector, apiUrl);
}

CitationsWidget.prototype.init = function() {
    var self = this;
    ko.applyBindings(self.viewModel, self.$element[0]);
};
//module.exports = MendeleySettings;
new CitationsWidget('#mendeleyWidget', '#mendeleyStyleSelect');
