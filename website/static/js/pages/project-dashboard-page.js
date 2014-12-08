/** Initialization code for the project dashboard. */

var $ = require('jquery');
require('jquery-tagsinput');

var Rubeus = require('rubeus');

var LogFeed = require('../logFeed.js');
var pointers = require('../pointers.js');

var Comment = require('../comment.js');
var Raven = require('raven-js');

// Since we don't have an Buttons/Status column, we append status messages to the
// name column
Rubeus.Col.DashboardName = $.extend({}, Rubeus.Col.Name);
Rubeus.Col.DashboardName.itemView = function(item) {
    return Rubeus.Col.Name.itemView(item) + '&nbsp;<span data-status></span>';
};

var nodeApiUrl = window.contextVars.node.urls.api;

var rubeusOpts = {
    data: nodeApiUrl + 'files/grid/',
    columns: [Rubeus.Col.DashboardName],
    width: '100%',
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

$(document).ready(function() {

    // Tooltips
    $('[data-toggle="tooltip"]').tooltip();

    // Tag input
    $('#node-tags').tagsInput({
        width: "100%",
        interactive: window.contextVars.currentUser.canEdit,
        maxChars: 128,
        onAddTag: function(tag){
            var url = window.contextVars.node.urls.api + "addtag/" + tag + "/";
            var request = $.ajax({
                url: url,
                type: "POST",
                contentType: "application/json"
            });
            request.fail(function(xhr, textStatus, error) {
                Raven.captureMessage('Failed to add tag', {
                    tag: tag, url: url, textStatus: textStatus, error: error
                });
            })
        },
        onRemoveTag: function(tag){
            var url = window.contextVars.node.urls.api + "removetag/" + tag + "/";
            var request = $.ajax({
                url: url,
                type: "POST",
                contentType: "application/json"
            });
            request.fail(function(xhr, textStatus, error) {
                Raven.captureMessage('Failed to remove tag', {
                    tag: tag, url: url, textStatus: textStatus, error: error
                });
            })
        }
    });

    // Limit the maximum length that you can type when adding a tag
    $('#node-tags_tag').attr("maxlength", "128");

    // Remove delete UI if not contributor
    if (!window.contextVars.currentUser.canEdit || window.contextVars.node.isRegistration) {
        $('a[title="Removing tag"]').remove();
        $('span.tag span').each(function(idx, elm) {
            $(elm).text($(elm).text().replace(/\s*$/, ''))
        });
    }

    if (window.contextVars.node.isRegistration && window.contextVars.node.tags.length === 0) {
        $('div.tags').remove();
    }

});