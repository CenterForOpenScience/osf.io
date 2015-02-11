/**
 * Controller for the rich citation widget on the project overview page.
 */
'use strict';

var $ = require('jquery');
var Raven = require('raven-js');

var $osf = require('osfHelpers');
require('select2');
require('../css/citations.css');

var locale = require('raw!../vendor/bower_components/locales/locales-en-US.xml');

var ctx = window.contextVars;

var formatResult = function(state) {
    return '<div class="citation-result-title">' + state.title + '</div>';
};

var formatSelection = function(state) {
    return state.title;
};

var makeCiteproc = function(style, citations, format) {
    format = format || 'html';
    var sys = {
        retrieveItem: function(id) {
            return citations[id];
        },
        retrieveLocale: function() {
            return locale;
        }
    };
    var citeproc = new CSL.Engine(sys, style);  // jshint ignore:line
    citeproc.setOutputFormat(format);
    citeproc.appendCitationCluster({
        citationItems: Object.keys(citations).map(function(key) {
            return {id: key};
        }),
        properties: {
            noteIndex: 0
        }
    });
    return citeproc;
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
    }).on('select2-selecting', function(event) {
        var styleUrl = '/static/vendor/bower_components/styles/' + event.val + '.csl';
        var styleRequest = $.get(styleUrl);
        var citationRequest = $.get(ctx.node.urls.api + 'citation/');
        $.when(styleRequest, citationRequest).done(function(style, citations) {
            var citeproc = makeCiteproc(style[0], citations[0], 'text');
            var items = citeproc.makeBibliography()[1];
            self.$citationElement.text(items[0]).slideDown();
        }).fail(function(jqxhr, status, error) {
            $osf.growl(
                'Citation render failed',
                'The requested citation format generated an error.',
                'danger'
            );
            Raven.captureMessage('Unexpected error when fetching citation', {
                url: styleUrl,
                citationStyle: event.val,
                status: status,
                error: error
            });
        });
    }).on('select2-removed', function (e) {
        self.$citationElement.slideUp().text();
    });

};

module.exports = CitationWidget;
