'use strict';

var $ = require('jquery');
var $osf = require('osfHelpers');
require('select2');
require('../css/citations.css');

var r = function(query) {
    query.callback({results: [
        {
            _id: "academy-of-management-review",
            summary: null,
            short_title: "AMR",
            title: "Academy of Management Review"
        }
    ]})
}

var formatResult = function(state) {
    return "<div class='citation-result-title'>" + state.title + "</div>";;
};

var formatSelection = function(state) {
    return state.title;
};

var input = $('#citationStyleInput');
var citationElement = $('#citationText');

input.select2({
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
            }
        },
        results: function(data, page) {
            return {results: data.styles}
        },
        cache: true
    }
}).on('select2-selecting', function(e) {
    var request = $.ajax({
        url: nodeApiUrl + 'citation/' + e.val
    });
    request.done(function (data) {
        citationElement.text(data.citation).slideDown();
    });
    request.fail(function() {
        $osf.growl(
            'Citation render failed',
            'The requested citation format generated an error.',
            'danger'
        );
    });
}).on('select2-removed', function (e) {
    citationElement.slideUp().text();
});