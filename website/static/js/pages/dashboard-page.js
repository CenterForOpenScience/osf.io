/**
 * Initialization code for the dashboard pages. Starts up the Project Organizer
 * and binds the onboarder Knockout components.
 * */
var Raven = require('raven-js');
var ko = require('knockout');
var $ = require('jquery');


var $osf = require('osfHelpers');
var ProjectOrganizer = require('../projectorganizer.js');
var LogFeed = require('../logFeed.js');
// Knockout components for the onboarder
require('../onboarder.js');

var url = '/api/v1/dashboard/get_nodes/';
var request = $.getJSON(url, function(response) {
    var allNodes = response.nodes;
    //  For uploads, only show nodes for which user has write or admin permissions
    var uploadSelection = ko.utils.arrayFilter(allNodes, function(node) {
        return $.inArray(node.permissions, ['write', 'admin']) !== -1;
    });
    // Filter out components and nodes for which user is not admin
    var registrationSelection = ko.utils.arrayFilter(uploadSelection, function(node) {
        return node.category === 'project' && node.permissions === 'admin';
    });

    $osf.applyBindings({nodes: allNodes}, '#obGoToProject');
    $osf.applyBindings({nodes: registrationSelection}, '#obRegisterProject');
    $osf.applyBindings({nodes: uploadSelection}, '#obUploader');

    function ProjectCreateViewModel() {
        var self = this;
        self.isOpen = ko.observable(false),
        self.focus = ko.observable(false);
        self.toggle = function() {
            self.isOpen(!self.isOpen());
            self.focus(self.isOpen());
        };
        self.nodes = response.nodes;
    }
    $osf.applyBindings(ProjectCreateViewModel, '#projectCreate');
});
request.fail(function(xhr, textStatus, error) {
    Raven.captureMessage('Could not fetch dashboard nodes.', {
        url: url, textStatus: textStatus, error: error
    });
});


// Initialize ProjectOrganizer
new ProjectOrganizer('#project-grid');

$(document).ready(function() {
    $('#projectOrganizerScope').tooltip({selector: '[data-toggle=tooltip]'});
});
// Initialize logfeed
new LogFeed('#logScope', '/api/v1/watched/logs/');
