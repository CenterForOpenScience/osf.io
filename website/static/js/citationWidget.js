/**
 * Controller for the rich citation widget on the project overview page.
 */
'use strict';

var $ = require('jquery');
var Raven = require('raven-js');
require('select2');

var $osf = require('./osfHelpers');
var citations = require('./citations');

require('../css/citations_widget.css');

var ctx = window.contextVars;

var formatResult = function(state) {
    // TODO: Investigate whether CSL requires escaping
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
        placeholder: 'Enter citation style (e.g. "APA")',
        minimumInputLength: 1,
        ajax: {
            url: '/api/v1/citations/styles/',
            quietMillis: 200,
            data: function(term, page) {
                return {
                    q: term
                };
            },
            results: function(data, page) {
                return {
                    results: data.styles
                };
            },
            cache: true
        }
    }).on('select2-selecting', function(event) {
        var styleUrl = '/static/vendor/bower_components/styles/' + event.val + '.csl';
        var styleRequest = $.get(styleUrl);
        var citationRequest = $.get(ctx.node.urls.api + 'citation/');
        $.when(styleRequest, citationRequest).done(function(style, data) {
            var citeproc = citations.makeCiteproc(style[0], data[0], 'html');
            var items = citeproc.makeBibliography()[1];
            /* the safety of this was discussed with JIRA ticket OSF-4889 */
            self.$citationElement.html(items[0]).slideDown();
        }).fail(function(jqxhr, status, error) {
            $osf.growl(
                'Citation render failed',
                'The requested citation format generated an error.',
                'danger'
            );
            Raven.captureMessage('Unexpected error when fetching citation', {
                extra: {
                    url: styleUrl,
                    citationStyle: event.val,
                    status: status,
                    error: error
                }
            });
        });
    }).on('select2-removed', function(e) {
        self.$citationElement.slideUp().text();
    });

};

module.exports = CitationWidget;
