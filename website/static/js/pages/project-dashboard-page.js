/** Initialization code for the project overview page. */
'use strict';

var $ = require('jquery');
require('jquery-tagsinput');
require('bootstrap-editable');
require('js/osfToggleHeight');

var m = require('mithril');
var Fangorn = require('js/fangorn');
var Raven = require('raven-js');
require('truncate');

var $osf = require('js/osfHelpers');
var LogFeed = require('js/logFeed');
var pointers = require('js/pointers');
var Comment = require('js/comment'); //jshint ignore:line
var NodeControl = require('js/nodeControl');
var CitationList = require('js/citationList');
var CitationWidget = require('js/citationWidget');
var mathrender = require('js/mathrender');
var md = require('js/markdown').full;
var NodesPrivacy = require('js/nodesPrivacy');

var ctx = window.contextVars;
var nodeApiUrl = ctx.node.urls.api;

// Listen for the nodeLoad event (prevents multiple requests for data)
$('body').on('nodeLoad', function(event, data) {
    if (!data.node.is_retracted) {
        // Initialize controller for "Add Links" modal
        new pointers.PointerManager('#addPointer', window.contextVars.node.title);
        new LogFeed('#logScope', nodeApiUrl + 'log/');
    }
    // Initialize CitationWidget if user isn't viewing through an anonymized VOL
    if (!data.node.anonymous && !data.node.is_retracted) {
        var citations = data.node.alternative_citations;
        new CitationList('#citationList', citations, data.user);
        new CitationWidget('#citationStyleInput', '#citationText');
    }
    // Initialize nodeControl
    new NodeControl.NodeControl('#projectScope', data);
    if (data.user.is_admin && !data.node.is_retracted) {
        new NodesPrivacy.NodesPrivacy('#nodesPrivacy', data.node.is_public);
    }
});

// Initialize comment pane w/ its viewmodel
var $comments = $('.comments');
if ($comments.length) {
    var options = {
        nodeId : window.contextVars.node.id,
        nodeApiUrl: window.contextVars.node.urls.api,
        isRegistration: window.contextVars.node.isRegistration,
        page: 'node',
        rootId: window.contextVars.node.id,
        fileId: null,
        canComment: window.contextVars.currentUser.canComment,
        hasChildren: window.contextVars.node.hasChildren,
        currentUser: window.contextVars.currentUser,
        pageTitle: window.contextVars.node.title
    };
    Comment.init('#commentsLink', '.comment-pane', options);
}
var institutionLogos = {
    controller: function(args){
        var self = this;
        self.institutions = args.institutions;
        self.nLogos = Math.min(self.institutions.length, 5);
        self.side = self.nLogos > 1 ? '35px': '75px';
        self.makeLogo = function(institution){
            return m('a', {href: '/institutions/' + institution.id},
                m('img.img-circle', {
                    height: self.side, width: self.side,
                    style: {margin: '3px'},
                    dataToggle: 'tooltip', dataPlacement: 'top', title: institution.name,
                    src: institution.logo_path
                })
            )
        }
    },
    view: function(ctrl, args){
        var tooltips = function(){
            $('[data-toggle="tooltip"]').tooltip();
        };
        return m('', {config: tooltips}, [$.map(ctrl.institutions, ctrl.makeLogo)]);
    }
};

$(document).ready(function () {

    m.mount(document.getElementById('instLogo'), m.component(institutionLogos, {institutions: window.contextVars.node.institutions}));
    $('#contributorsList').osfToggleHeight();
    if (!ctx.node.isRetracted) {
        // Treebeard Files view
        $.ajax({
            url:  nodeApiUrl + 'files/grid/'
        }).done(function (data) {
            var fangornOpts = {
                divID: 'treeGrid',
                filesData: data.data,
                uploads : true,
                showFilter : true,
                placement: 'dashboard',
                title : undefined,
                filterFullWidth : true, // Make the filter span the entire row for this view
                xhrconfig: $osf.setXHRAuthorization,
                columnTitles : function () {
                    return [
                        {
                            title: 'Name',
                            width : '100%',
                            sort : true,
                            sortType : 'text'
                        }
                    ];
                },
                resolveRows : function (item) {
                    var tb = this;
                    item.css = '';
                    if(tb.isMultiselected(item.id)){
                        item.css = 'fangorn-selected';
                    }
                    if(item.data.permissions && !item.data.permissions.view){
                        item.css += ' tb-private-row';
                    }
                    var defaultColumns = [
                                {
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
                    if(item.data.uploadState && (item.data.uploadState() === 'pending' || item.data.uploadState() === 'uploading')){
                        return Fangorn.Utils.uploadRowTemplate.call(tb, item);
                    }

                    var configOption = Fangorn.Utils.resolveconfigOption.call(this, item, 'resolveRows', [item]);
                    return configOption || defaultColumns;
                }
            };
            var filebrowser = new Fangorn(fangornOpts);
        });
    }

    // Tooltips
    $('[data-toggle="tooltip"]').tooltip({container: 'body'});

    // Tag input
    $('#node-tags').tagsInput({
        width: '100%',
        interactive: window.contextVars.currentUser.canEdit,
        maxChars: 128,
        onAddTag: function(tag){
            var url = nodeApiUrl + 'tags/';
            var data = {tag: tag};
            var request = $osf.postJSON(url, data);
            request.fail(function(xhr, textStatus, error) {
                Raven.captureMessage('Failed to add tag', {
                    extra: {
                        tag: tag, url: url, textStatus: textStatus, error: error
                    }
                });
            });
        },
        onRemoveTag: function(tag){
            var url = nodeApiUrl + 'tags/';
            var data = JSON.stringify({tag: tag});
            var request = $.ajax({
                url: url,
                type: 'DELETE',
                contentType: 'application/json',
                dataType: 'JSON',
                data: data
            });
            request.fail(function(xhr, textStatus, error) {
                Raven.captureMessage('Failed to remove tag', {
                    extra: {
                        tag: tag, url: url, textStatus: textStatus, error: error
                    }
                });
            });
        }
    });

    //Clear input fields on Add Component Modal
    $('#confirm').on('click', function () {
        $('#alert').text('');
        $('#title').val('');
        $('#category').val('');
    });

    // only focus input field on modals when not IE
    $('#newComponent').on('shown.bs.modal', function(){
        if(!$osf.isIE()){
            $('#title').focus();
        }
    });

    $('#newComponent').on('hidden.bs.modal', function(){
        $('#newComponent .modal-alert').text('');
    });

    $('#addPointer').on('shown.bs.modal', function(){
        if(!$osf.isIE()){
            $('#addPointer input').focus();
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
    $('a.btn').mouseup(function(){
        $(this).blur();
    });
});
