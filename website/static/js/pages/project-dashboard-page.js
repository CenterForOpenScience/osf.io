/** Initialization code for the project overview page. */
'use strict';

var $ = require('jquery');
require('../../vendor/bower_components/jquery.tagsinput/jquery.tagsinput.css');
require('jquery-tagsinput');

var m = require('mithril');
var Fangorn = require('fangorn');

var LogFeed = require('../logFeed.js');
var pointers = require('../pointers.js');

var Comment = require('../comment.js');
var Raven = require('raven-js');

var NodeControl = require('../nodeControl.js');

var CitationList = require('../citationList.js');
var CitationWidget = require('../citationWidget.js');

var mathrender = require('mathrender');
var md = require('markdown').full;
require('truncate');

var ctx = window.contextVars;
var nodeApiUrl = ctx.node.urls.api;

// Initialize controller for "Add Links" modal
new pointers.PointerManager('#addPointer', window.contextVars.node.title);

// Listen for the nodeLoad event (prevents multiple requests for data)
$('body').on('nodeLoad', function(event, data) {
    new LogFeed('#logScope', nodeApiUrl + 'log/');
    // Initialize nodeControl
    new NodeControl('#projectScope', data);
});

// Initialize comment pane w/ it's viewmodel
var $comments = $('#comments');
if ($comments.length) {
    var userName = window.contextVars.currentUser.name;
    var canComment = window.contextVars.currentUser.canComment;
    var hasChildren = window.contextVars.node.hasChildren;
    Comment.init('#commentPane', userName, canComment, hasChildren);
}

// Initialize CitationWidget if user isn't viewing through an anonymized VOL
if (!ctx.node.anonymous) {
    new CitationList('#citationList');
    new CitationWidget('#citationStyleInput', '#citationText');
}

$(document).ready(function() {
    // Treebeard Files view
    $.ajax({
        url:  nodeApiUrl + 'files/grid/'
    })
    .done(function( data ) {
        var fangornOpts = {
            divID: 'treeGrid',
            filesData: data.data,
            uploads : true,
            showFilter : true,
            placement: 'dashboard',
            title : undefined,
            filterFullWidth : true, // Make the filter span the entire row for this view
            columnTitles : function(){
                return [
                    {
                    title: 'Name',
                    width : '100%',
                    sort : true,
                    sortType : 'text'
                    }
                ];
            },
            resolveRows : function(item){
                var defaultColumns = [{
                    data: 'name',
                    folderIcons: true,
                    filter: true,
                    custom: Fangorn.DefaultColumns._fangornTitleColumn
                }];

                if (item.parentID) {
                    item.data.permissions = item.data.permissions || item.parent().data.permissions;
                    if (item.data.kind === 'folder') {
                        item.data.accept = item.data.accept || item.parent().data.accept;
                    }
                }

                if(item.data.tmpID){
                    defaultColumns = [
                        {
                            data : 'name',  // Data field name
                            folderIcons : true,
                            filter : true,
                            custom : function(){ return m('span.text-muted', 'Uploading ' + item.data.name + '...'); }
                        }
                    ];
                }

                var configOption = Fangorn.Utils.resolveconfigOption.call(this, item, 'resolveRows', [item]);
                return configOption || defaultColumns;
            }
        };
        var filebrowser = new Fangorn(fangornOpts);
    });

    // Tooltips
    $('[data-toggle="tooltip"]').tooltip({container: 'body'});

    // Tag input
    $('#node-tags').tagsInput({
        width: '100%',
        interactive: window.contextVars.currentUser.canEdit,
        maxChars: 128,
        onAddTag: function(tag){
            var url = window.contextVars.node.urls.api + 'addtag/' + tag + '/';
            var request = $.ajax({
                url: url,
                type: 'POST',
                contentType: 'application/json'
            });
            request.fail(function(xhr, textStatus, error) {
                Raven.captureMessage('Failed to add tag', {
                    tag: tag, url: url, textStatus: textStatus, error: error
                });
            });
        },
        onRemoveTag: function(tag){
            var url = window.contextVars.node.urls.api + 'removetag/' + tag + '/';
            var request = $.ajax({
                url: url,
                type: 'POST',
                contentType: 'application/json'
            });
            request.fail(function(xhr, textStatus, error) {
                Raven.captureMessage('Failed to remove tag', {
                    tag: tag, url: url, textStatus: textStatus, error: error
                });
            });
        }
    });

    // Limit the maximum length that you can type when adding a tag
    $('#node-tags_tag').attr('maxlength', '128');

    // Wiki widget markdown rendering
    if (ctx.wikiWidget) {
        // Render math in the wiki widget
        var markdownElement = $('#markdownRender');
        mathrender.mathjaxify(markdownElement);

        // Render the raw markdown of the wiki
        if (!ctx.usePythonRender) {
            var request = $.ajax({
                url: ctx.urls.wikiContent
            });
            request.done(function(resp) {
                var rawText = resp.wiki_content || '*No wiki content*';
                var renderedText = md.render(rawText);
                var truncatedText = $.truncate(renderedText, {length: 400});
                markdownElement.html(truncatedText);
                mathrender.mathjaxify(markdownElement);
            });
        }
    }

    // Remove delete UI if not contributor
    if (!window.contextVars.currentUser.canEdit || window.contextVars.node.isRegistration) {
        $('a[title="Removing tag"]').remove();
        $('span.tag span').each(function(idx, elm) {
            $(elm).text($(elm).text().replace(/\s*$/, ''));
        });
    }

    if (window.contextVars.node.isRegistration && window.contextVars.node.tags.length === 0) {
        $('div.tags').remove();
    }

});
