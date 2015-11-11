'use strict';
var $ = require('jquery');
var $osf = require('js/osfHelpers');
var Raven = require('raven-js');
var ko = require('knockout');
require('js/qToggle');
require('js/onboarder.js');
require('js/components/autocomplete');

$(function(){
    $('.prereg-button').qToggle();
    $('.prereg-button').click(function(){
        var target = $(this).attr('data-qToggle-target');
        $(target).find('input').first().focus();
    });

    // Activate "existing projects" typeahead.
    var url = '/api/v1/dashboard/get_nodes/';
    $.getJSON(url).done(function(response) {
        var allNodes = response.nodes;

        // If we need to change what nodes can be registered, filter here
        var registrationSelection = ko.utils.arrayFilter(allNodes, function(node) {
            return $.inArray(node.permissions, ['admin']) !== -1;
        });

        $osf.applyBindings({
            nodes: registrationSelection,
            enableComponents: true
        }, '#existingProject');
    }).fail(function(xhr, textStatus, error) {
        Raven.captureMessage('Could not fetch dashboard nodes.', {
            url: url, textStatus: textStatus, error: error
        });
    });

    // Activate autocomplete for draft registrations
    $osf.applyBindings({}, '#existingPrereg');
});
