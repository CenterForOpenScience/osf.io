/** Initialization code for the project dashboard. */

var $ = require('jquery');
var Rubeus = require('rubeus');

var LogFeed = require('../logFeed.js');
var pointers = require('../pointers.js');

var Comment = require('../comment.js');
var $osf = require('osf-helpers');
var bootbox = require('bootbox');
var Raven = require('raven-js');


// Since we don't have an Buttons/Status column, we append status messages to the
// name column
Rubeus.Col.DashboardName = $.extend({}, Rubeus.Col.Name);
Rubeus.Col.DashboardName.itemView = function(item) {
    return Rubeus.Col.Name.itemView(item) + '&nbsp;<span data-status></span>';
};
var rubeusOpts = {
    data: nodeApiUrl + 'files/grid/',
    columns: [Rubeus.Col.DashboardName],
    width: "100%",
    uploads: true,
    height: 600,
    progBar: '#filetreeProgressBar',
    searchInput: '#fileSearch'
};
new Rubeus('#myGrid', rubeusOpts);

// Initialize controller for "Add Links" modal
new pointers.PointerManager('#addPointer', window.contextVars.node.title);

// Listen for the nodeLoad event (prevents multiple requests for data)
$('body').on('nodeLoad', function() {
    new LogFeed('#logScope', nodeApiUrl + 'log/');
});


// Initialize comment pane w/ it's viewmodel
var $comments = $('#comments');
if ($comments.length) {
    var userName = window.contextVars.currentUser.name;
    var canComment = window.contextVars.currentUser.canComment;
    var hasChildren = window.contextVars.node.hasChildren;
    Comment.init('#commentPane', userName, canComment, hasChildren);
}

// Widget config error
$(document).ready(function() {
    $(".widget-disable").click(function() {
        var fullName = '${full_name | js_str}';
        var url = '${node['api_url']}${short_name | js_str}/settings/disable/';

        var req = $osf.postJSON(url, {});

        req.done(function() {
            location.reload();
        });

        req.fail(function(jqxhr, status, error) {
            bootbox.alert('Unable to disable ' + fullName);
            Raven.captureMessage('Error while attempting to disable ' + fullName, {
                url: url, status: status, error: error
            });
        })
    });
});
