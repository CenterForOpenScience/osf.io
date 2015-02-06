/**
 * Controller for the rich citation widget on the project overview page.
 */
'use strict';

var $ = require('jquery');
var Raven = require('raven-js');

var $osf = require('osfHelpers');
require('select2');
require('../css/citations.css');

var ctx = window.contextVars;

var r = function(query) {
    query.callback({results: [
        {
            _id: 'academy-of-management-review',
            summary: null,
            short_title: 'AMR',
            title: 'Academy of Management Review'
        }
    ]});
};

var formatResult = function(state) {
    return '<div class="citation-result-title">' + state.title + '</div>';
};

var formatSelection = function(state) {
    return state.title;
};

// Public API

function CitationWidget(inputSelector, displaySelector) {
    this.$input = $(inputSelector || '#citationStyleInput');
    this.$citationElement = $(displaySelector || '#citationText');
    this.init();
}
CitationWidget.prototype.init = function() {
    var self = this;
    // Initialize select2 for selecting citation style
    self.$input.select2({
        allowClear: true,
        formatResult: formatResult,
        formatSelection: formatSelection,
        placeholder: 'Citation Style (e.g. "APA")',
        minimumInputLength: 1,
        ajax: {
            url: '/api/v1/citations/styles/',
            quietMillis: 200,
            data: function(term, page) {
                return {
                    'q': term
                };
            },
            results: function(data, page) {
                return {results: data.styles};
            },
            cache: true
        }
    }).on('select2-selecting', function(e) {
        var url = ctx.node.urls.api + 'citation/' + e.val;
        var request = $.ajax({
            url: url
        });
        request.done(function (data) {
            self.$citationElement.text(data.citation).slideDown();
        });
        request.fail(function(jqxhr, status, error) {
            $osf.growl(
                'Citation render failed',
                'The requested citation format generated an error.',
                'danger'
            );
            Raven.captureMessage('Unexpected error when fetching citation', {
                url: url, citationStyle: e.val, status: status, error: error
            });
        });
    }).on('select2-removed', function (e) {
        self.$citationElement.slideUp().text();
    });

};
module.exports = CitationWidget;
