/** Initialization code for the project overview page. */
'use strict';

var $ = require('jquery');
require('jquery-tagsinput');
require('bootstrap-editable');
require('js/osfToggleHeight');

var m = require('mithril');
var Fangorn = require('js/fangorn').Fangorn;
var Raven = require('raven-js');
require('truncate');

var $osf = require('js/osfHelpers');
var LogFeed = require('js/components/logFeed');
var pointers = require('js/pointers');
var Comment = require('js/comment'); //jshint ignore:line
var NodeControl = require('js/nodeControl');
var CitationList = require('js/citationList');
var CitationWidget = require('js/citationWidget');
var mathrender = require('js/mathrender');
var md = require('js/markdown').full;
var oldMd = require('js/markdown').old;
var AddProject = require('js/addProjectPlugin');
var SocialShare = require('js/components/socialshare');

var ctx = window.contextVars;
var node = window.contextVars.node;
var nodeApiUrl = ctx.node.urls.api;
var nodeCategories = ctx.nodeCategories || [];


// Listen for the nodeLoad event (prevents multiple requests for data)
$('body').on('nodeLoad', function(event, data) {
    if (!data.node.is_retracted) {
        // Initialize controller for "Add Links" modal
        new pointers.PointerManager('#addPointer', window.contextVars.node.title);
    }
    // Initialize CitationWidget if user isn't viewing through an anonymized VOL
    if (!data.node.anonymous && !data.node.is_retracted) {
        new CitationList('#citationList');
        new CitationWidget('#citationStyleInput', '#citationText');
    }
    // Initialize nodeControl
    new NodeControl.NodeControl('#projectScope', data, {categories: nodeCategories});
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
        currentUser: window.contextVars.currentUser,
        pageTitle: window.contextVars.node.title,
        inputSelector: '.atwho-input'
    };
    Comment.init('#commentsLink', '.comment-pane', options);
}
var institutionLogos = {
    controller: function(args){
        var self = this;
        self.institutions = args.institutions;
        self.nLogos = self.institutions.length;
        self.side = self.nLogos > 1 ? (self.nLogos === 2 ? '50px' : '35px') : '75px';
        self.width = self.nLogos > 1 ? (self.nLogos === 2 ? '115px' : '86px') : '75px';
        self.makeLogo = function(institution){
            return m('a', {href: '/institutions/' + institution.id},
                m('img', {
                    height: self.side, width: self.side,
                    style: {margin: '3px'},
                    title: institution.name,
                    src: institution.logo_path
                })
            );
        };
    },
    view: function(ctrl, args){
        var tooltips = function(){
            $('[data-toggle="tooltip"]').tooltip();
        };
        var instCircles = $.map(ctrl.institutions, ctrl.makeLogo);
        if (instCircles.length > 4){
            instCircles[3] = m('.fa.fa-plus-square-o', {
                style: {margin: '6px', fontSize: '250%', verticalAlign: 'middle'},
            });
            instCircles.splice(4);
        }

        return m('', {style: {float: 'left', width: ctrl.width, textAlign: 'center', marginRight: '10px'}, config: tooltips}, instCircles);
    }
};


$(document).ready(function () {

    var AddComponentButton = m.component(AddProject, {
        buttonTemplate: m('.btn.btn-sm.btn-default[data-toggle="modal"][data-target="#addSubComponent"]', {onclick: function() {
            $osf.trackClick('project-dashboard', 'add-component', 'open-add-project-modal');
        }}, 'Add Component'),
        modalID: 'addSubComponent',
        title: 'Create new component',
        parentID: window.contextVars.node.id,
        parentTitle: window.contextVars.node.title,
        categoryList: nodeCategories,
        stayCallback: function() {
            // We need to reload because the components list needs to be re-rendered serverside
            window.location.reload();
        },
        trackingCategory: 'project-dashboard',
        trackingAction: 'add-component',
        contributors: window.contextVars.node.contributors,
        currentUserCanEdit: window.contextVars.currentUser.canEdit
    });

    if (!ctx.node.isRetracted) {
        if (ctx.node.institutions.length && !ctx.node.anonymous) {
            m.mount(document.getElementById('instLogo'), m.component(institutionLogos, {institutions: window.contextVars.node.institutions}));
        }
        $('#contributorsList').osfToggleHeight();

        // Recent Activity widget
        m.mount(document.getElementById('logFeed'), m.component(LogFeed.LogFeed, {node: node}));

        // Treebeard Files view
        var urlFilesGrid = nodeApiUrl + 'files/grid/';
        var promise = m.request({ method: 'GET', config: $osf.setXHRAuthorization, url: urlFilesGrid});
        promise.then(function (data) {
            var fangornOpts = {
                divID: 'treeGrid',
                filesData: data.data,
                allowMove: !node.isRegistration,
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
                            width : '70%',
                            sort : true,
                            sortType : 'text'
                        },
                        {
                            title: 'Modified',
                            width : '30%',
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
                                custom: Fangorn.DefaultColumns._fangornTitleColumn},
                                {
                                data: 'modified',
                                folderIcons: false,
                                filter: false,
                                custom: Fangorn.DefaultColumns._fangornModifiedColumn
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
            var newComponentElem = document.getElementById('newComponent');
            if (window.contextVars.node.isPublic) {
                m.mount(
                    document.getElementById('shareButtonsPopover'),
                    m.component(
                        SocialShare.ShareButtonsPopover,
                        {title: window.contextVars.node.title, url: window.location.href}
                    )
                );
            }
            if (newComponentElem) {
                m.mount(newComponentElem, AddComponentButton);
            }
            return promise;
        }, function(xhr, textStatus, error) {
            Raven.captureMessage('Error retrieving filebrowser', {extra: {url: urlFilesGrid, textStatus: textStatus, error: error}});
        }

      );

    }

    // Tooltips
    $('[data-toggle="tooltip"]').tooltip({container: 'body'});

    // Tag input
    var nodeType = window.contextVars.node.isRegistration ? 'registrations':'nodes';
    var tagsApiUrl = $osf.apiV2Url(nodeType + '/' + window.contextVars.node.id + '/');
    $('#node-tags').tagsInput({
        width: '100%',
        interactive: window.contextVars.currentUser.canEditTags,
        maxChars: 128,
        defaultText: 'Add a tag to enhance discoverability',
        onAddTag: function(tag) {
            $('#node-tags_tag').attr('data-default', 'Add a tag');
            window.contextVars.node.tags.push(tag);
            var payload = {
                data: {
                    type: nodeType,
                    id: window.contextVars.node.id,
                    attributes: {
                        tags: window.contextVars.node.tags
                    }
                }
            };

            var request = $osf.ajaxJSON(
                'PATCH',
                tagsApiUrl,
                {
                    data: payload,
                    isCors: true
                }
            );

            request.fail(function(xhr, textStatus, error) {
                window.contextVars.node.tags.splice(window.contextVars.node.tags.indexOf(tag),1);
                Raven.captureMessage('Failed to add tag', {
                    extra: {
                        tag: tag, url: tagsApiUrl, textStatus: textStatus, error: error
                    }
                });
            });
        },
        onRemoveTag: function(tag) {
            if (!tag) {
                return false;
            }
            window.contextVars.node.tags.splice(window.contextVars.node.tags.indexOf(tag),1);
            var payload = {
                data: {
                    type: nodeType,
                    id: window.contextVars.node.id,
                    attributes: {
                        tags: window.contextVars.node.tags
                    }
                }
            };

            var request = $osf.ajaxJSON(
                'PATCH',
                tagsApiUrl,
                {
                    data: payload,
                    isCors: true
                }
            );

            request.fail(function(xhr, textStatus, error) {
                window.contextVars.node.tags.push(tag);
                // Suppress "tag not found" errors, as the end result is what the user wanted (tag is gone)- eg could be because two people were working at same time
                if (xhr.status !== 409) {
                    $osf.growl('Error', 'Could not remove tag');
                    Raven.captureMessage('Failed to remove tag', {
                        extra: {
                            tag: tag, url: tagsApiUrl, textStatus: textStatus, error: error
                        }
                    });
                }
            });
        }
    });

    // allows inital default message to fit on empty tag
    if(!$('.tag').length){
        $('#node-tags_tag').css('width', '250px');
    }

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
        var request = $.ajax({
            url: ctx.urls.wikiContent
        });
        request.done(function(resp) {
            var rawText = resp.wiki_content || '*Add important information, links, or images here to describe your project.*';
            var renderedText = ctx.renderedBeforeUpdate ? oldMd.render(rawText) : md.render(rawText);
            // don't truncate the text when length = 400
            var truncatedText = $.truncate(renderedText, {length: 401});
            markdownElement.html(truncatedText);
            mathrender.mathjaxify(markdownElement);
            markdownElement.show();
        });
    }

    // Remove delete UI if not contributor
    if (!window.contextVars.currentUser.canEditTags) {
        $('a[title="Removing tag"]').remove();
        $('span.tag span').each(function(idx, elm) {
            $(elm).text($(elm).text().replace(/\s*$/, ''));
        });
    }
});
