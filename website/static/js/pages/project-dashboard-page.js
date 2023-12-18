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
var currentUserRequestState = ctx.currentUserRequestState;

var _ = require('js/rdmGettext')._;
var sprintf = require('agh.sprintf').sprintf;

var datepicker = require('js/rdmDatepicker');
require('js/rdmSelect2');

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
    new NodeControl.NodeControl('#projectScope', data, {categories: nodeCategories, currentUserRequestState: currentUserRequestState});

    // Enable the otherActionsButton once the page is loaded so the menu is properly populated
    $('#otherActionsButton').removeClass('disabled');
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

var ArrangeLogDownload = function (){};
var RefreshLog = function(){};

var useDropdownUsers = true;
var selectFromAllUsers = false;

// NOTE: The feature of free input style to filter users is hidden.
$('#useDropdown').hide();

var message_filter_by_users = _('Filter by users');
var message_select_from_contributors = _('Select from current contributors');
var message_select_from_all_users = _('Select including past contributors');
var message_select_from_all_users_checkbox = _('Include past project contributors in your search');
var message_use_dropdown_menu = _('Use dropdown menu');

var commonDropdownSuggestOptions = {
    sortResults: function(results, container, query) {
        return results.sort(function(a, b) {
            if (a.text > b.text) {
                return 1;
            } else if (a.text < b.text) {
                return -1;
            } else {
                return 0;
            }
        });
    },
    multiple: true,
    allowClear: true,
    cache: true,
    width: '100%'
};

var initDropdownSuggestAllUsers = function (placeholder) {
    var options = {
        ajax: {
	    url: $osf.apiV2Url('/users/'),
	    dataType: 'json',
	    data: function (term, page) {
		return {
		  'filter[id,full_name][icontains]': term,
		};
	    },
	    results: function (data, page, query) {
		var users = [];
		for (var i in data.data) {
		    var d = data.data[i];
		    var userAttr = d.attributes;
		    var guid = d.id.toUpperCase();
		    // OSFUser.fullname
		    var name = userAttr.full_name + ' @' + guid;
		    users.push({id: userAttr.uid, text: name});
		}
		return {
		    results: users
		};
	    },
            placeholder: placeholder
	},
        minimumInputLength: 1,
        formatInputTooShort: function (input, min) {
           var n = min - input.length;
           return sprintf(_('Please enter %s or more characters'), n);
        }
    };
    $.extend(true, options, commonDropdownSuggestOptions);
    $('#LogSearchName').select2(options);
};

var initDropdownSuggestContributors = function (placeholder) {
    var contributors = window.contextVars.node.contributors;
    var makeData = function (user) {
        var full_name = user.fullname;
        if (full_name === null) {
            full_name = '';
        }
        var guid = user.id.toUpperCase();
        var name = full_name + ' @' + guid;
        return {id: user.primary_key, text: name};
    };
    var options = {
        data: $.map(contributors, makeData),
        placeholder: placeholder
    };
    $.extend(true, options, commonDropdownSuggestOptions);
    $('#LogSearchName').select2(options);
};

// old implementation to search users for Recent Activity
var getUserKeysByPartialMatch = function (inputStr, updateLog, urlFilesGrid) {
    var splitSearch = function(searchStr) {
        // Examples:
	// a b c de -> [['a'], ['b'], ['c'], ['de']]
	// "a b c" de -> [['a b c'], ['de']]
	// "a\ b c" de -> [['a\ b c'], ['de']]
	// "a b c de -> [['a b c de']]
	// a\ b\ c de -> [['a b c'], ['de']]
	// "a b" AND c de -> [['a b', 'c'], ['de']]
	// "a b" "AND" c de -> [['a b', 'c'], ['de']]
	// a \"AND\" \b \\ \" -> [['a'], ['AND'], ['b'], ['\'], ['"']]
	var words = [];
	var all = Array.from(searchStr);
	var len = all.length;
	var i;
	var escape = false;
	var quote = false;
	var tmp = [];

	var confirm = function() {
	    if (tmp.length > 0) {
		words.push(tmp.join(''));
		tmp = [];
	    }
	};

	for (i = 0; i < len; i++) {
	    var c = all[i];
	    if (quote) {
		if (c === '"') {
		   confirm();
		   quote = false;
		} else {
		    tmp.push(c);
		}
	    } else if (escape) {
		tmp.push(c);
		escape = false;
	    } else if (c === ' ') {
		confirm();
		escape = false;
	    } else if (c === '\\') {
		escape = true;
	    } else if (c === '"') {
		confirm();
		quote = true;
	    } else {
		tmp.push(c);
		escape = false;
	    }
	}
	confirm();

	var results = [];
	var and_list = [];
	len = words.length;
	for (i = 0; i < len; i++) {
	    var word = words[i];
	    var next = null;
	    if (i < len - 1) {
		next = words[i+1];
	    }
	    if (word === 'AND') {
		continue;
	    } else {
		if (word === '"AND"') {
		    word = 'AND';
		}
		if (word !== '') {
		  and_list.push(word);
		}
		if (next !== 'AND') {
		   if (and_list.length > 0) {
		     results.push(and_list);
		     and_list = [];
		   }
		}
	    }
	}
	return results;
    };

    var logSearchNames = splitSearch(inputStr);
    var urlUsers = $osf.apiV2Url('/users/');
    var userKeyDict = {};
    var promise = m.request({
        method: 'GET',
        config: $osf.setXHRAuthorization,
        url: urlUsers});
    promise.then(function (data) {
        var total = Number(data.links.meta.total);
        var name_i;
        for (name_i in logSearchNames) {
            var and_list = logSearchNames[name_i];
            if (and_list.length === 0) {
                continue;
            }
            var data_i;
            for (data_i in data.data) {
                var userAttr = data.data[data_i].attributes;
                // OSFUser.fullname
                var fullName = userAttr.full_name;
                var j;
                var match_count = 0;
                for (j = 0; j < and_list.length; j++) {
                    var word = and_list[j];
                    if (fullName.includes(word)) {
                        match_count++;
                    }
                }
                if (match_count === and_list.length) {
                    // OSFUser.id
                    userKeyDict[userAttr.uid] = true;
                }
            }
        }
        var userKeysList = Object.keys(userKeyDict);
        if (userKeysList.length === 0) {
            // $osf.growl(_('no user matched'), '"' + LogSearchName + '"', 'warning');
            updateLog(null);  // show empty log
        } else {
            updateLog(userKeysList.join(','));
        }
    }, function(xhr, textStatus, error) {
        Raven.captureMessage('Error retrieving UserList', {extra:
           {url: urlFilesGrid, textStatus: textStatus, error: error}});
    });
};

var initUserKeysForRecentActivity = function () {
    var init = function () {
        var makePlaceholder = function (a, b) {
            return a + ' (' + b + ')';
        };
        var placeholder = '';

        $('#LogSearchName').select2('destroy');
        if (useDropdownUsers) {
            if (selectFromAllUsers) {
                placeholder = makePlaceholder(message_filter_by_users, message_select_from_all_users);
                initDropdownSuggestAllUsers(placeholder);
            } else {
                placeholder = makePlaceholder(message_filter_by_users, message_select_from_contributors);
                initDropdownSuggestContributors(placeholder);
            }
        } else {
            $('#LogSearchName').css('width', '100%');
            placeholder = message_filter_by_users;
        }
        $('#LogSearchName').attr('placeholder', placeholder);
    };

    var clearLogFilterUsers = function () {
        $('#LogSearchName').select2('val', '');
    };

    var clearLogFilter = function () {
        if (useDropdownUsers) {
            clearLogFilterUsers();
        } else {
            $('#LogSearchName').val(null);
        }
        $('#LogSearchS').val(null);
        $('#LogSearchE').val(null);
        RefreshLog();
    };
    $('#ClearLogFilterBtn').on('click', clearLogFilter);

    $('#RefreshLog').on('click', RefreshLog);
    $('#LogSearchName').on('change', RefreshLog);
    $('#LogSearchName,#LogSearchE,#LogSearchS').on('keypress', function(e){
        var key = e.which;
        if (key === 13) {  // Enter Key
            new RefreshLog();
            return false;
        }
    });

    $('#useDropdownLabel').text(message_use_dropdown_menu);
    $('#fromAllUsersLabel').text(message_select_from_all_users_checkbox);

    // set defaults
    $('#useDropdownCheckbox').prop('checked', true);
    $('#fromAllUsersCheckbox').prop('checked', false);
    init();

    $('#useDropdownCheckbox').change(function() {
        useDropdownUsers = $('#useDropdownCheckbox').is(':checked');
        $('#fromAllUsers').toggle(useDropdownUsers);
        init();
        clearLogFilter();
    });
    $('#fromAllUsersCheckbox').change(function() {
        selectFromAllUsers = $('#fromAllUsersCheckbox').is(':checked');
        init();
        clearLogFilterUsers();
        RefreshLog();
    });
};

var updateUserKeysForRecentActivity = function (LogSearchName, updateLog, urlFilesGrid) {
    if (useDropdownUsers) {
        updateLog(LogSearchName);
    } else { // old implementation
        getUserKeysByPartialMatch(LogSearchName, updateLog, urlFilesGrid);
    }
};

$(document).ready(function () {
    // Allows dropdown elements to persist after being clicked
    // Used for the "Share" button in the more actions menu
    $('.dropdown').on('click', 'li', function (evt) {
        var target = $(evt.target);
        // If the clicked element has .keep-open, don't allow the event to propagate
        return !(target.hasClass('keep-open') || target.parents('.keep-open').length);
    });

    var AddComponentButton = m.component(AddProject, {
        buttonTemplate: m('.btn.btn-sm.btn-default[data-toggle="modal"][data-target="#addSubComponent"]', {onclick: function() {
            $osf.trackClick('project-dashboard', 'add-component', 'open-add-project-modal');
        }}, _('Add Component')),
        modalID: 'addSubComponent',
        title: _('Create new component'),
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
        m.mount(document.getElementById('logFeed'), m.component(LogFeed.LogFeed, {node: node, noTarget: false}));

        //Download Log button

        ArrangeLogDownload = function (d){
            var i, NodeLogs=[], x={};
            for (i in d.data){
                x={'date': new Date(d.data[i].attributes.date + 'Z').toLocaleString(),
                   'user': d.data[i].embeds.user.data.attributes.full_name,
                   'project_id': d.data[i].attributes.params.params_node.id,
                   'project_title': d.data[i].attributes.params.params_node.title,
                   'action':  d.data[i].attributes.action,
                   };
                if (typeof d.data[i].attributes.params.contributors[0] !== 'undefined' && d.data[i].attributes.params.contributors[0] !== null) {
                    x.targetUserFullId = d.data[i].attributes.params.contributors[0].id;
                    x.targetUserFullName = d.data[i].attributes.params.contributors[0].full_name;
                }
                if (d.data[i].attributes.action.includes('checked')){
                    x.item = d.data[i].attributes.params.kind;
                    x.path = d.data[i].attributes.params.path;
                }
                if (d.data[i].attributes.action.includes('osf_storage')){
                    x.path = d.data[i].attributes.params.path;
                }
                if (d.data[i].attributes.action.includes('addon')){
                    x.addon = d.data[i].attributes.params.addon;
                }
                if (d.data[i].attributes.action.includes('tag')){
                    x.tag = d.data[i].attributes.params.tag;
                }
                if (d.data[i].attributes.action.includes('wiki')){
                    x.version = d.data[i].attributes.params.version;
                    x.page = d.data[i].attributes.params.page;
                }
                NodeLogs = NodeLogs.concat(x);
            }
            $('<a />', {
                'download': 'NodeLogs_'+ node.id + '_' + $.now() + '.json', 'href' : 'data:application/json;charset=utf-8,' + encodeURIComponent(JSON.stringify({'NodeLogs': NodeLogs})),
            }).appendTo('body')
             .click(function() {
                $(this).remove();
            })[0].click();
        };
        $('#DownloadLog').on('click', function(){
            var urlPrefix = (node.isRegistration || node.is_registration) ? 'registrations' : 'nodes';
            var query = { 'embed' : 'user'};
            var urlMain = $osf.apiV2Url(urlPrefix + '/' + node.id + '/logs/',{query: query});
            var urlNodeLogs = urlMain + '&page[size]=1';
            var promise = m.request({ method: 'GET', config: $osf.setXHRAuthorization, url: urlNodeLogs});
            promise.then(function (data) {
                var pageSize = Math.ceil((Number(data.links.meta.total))/(Number(data.links.meta.per_page)));
                if ( pageSize >= 2){
                    urlNodeLogs =  urlMain + '&page[size]=' + pageSize.toString();
                    promise = m.request({ method: 'GET', config: $osf.setXHRAuthorization, url: urlNodeLogs});
                    promise.then(function(data){
                        new ArrangeLogDownload(data);
                    });
                }else{
                    new ArrangeLogDownload(data);
                }
            }, function(xhr, textStatus, error) {
                Raven.captureMessage('Error retrieving DownloadLog', {extra: {url: urlFilesGrid, textStatus: textStatus, error: error}});
            });
        });

        // Refresh button
        RefreshLog = function () {
            var LogSearchName = $('#LogSearchName').val();
            if (LogSearchName === '') {
                $('#LogSearchUserKeys').val('');
                m.mount(document.getElementById('logFeed'),
                         m.component(LogFeed.LogFeed,
                                     {node: node, noTarget: false}));
            } else {
                // $osf.growl('DEBUG', '"' + LogSearchName + '"', 'warning', 10000);
                var updateLog = function (userKeys) {
                    var noTarget = false;
                    if (userKeys === null) {
                        noTarget = true;
                    }
                    // userKeys === '' ... not filtered (get all users)
                    $('#LogSearchUserKeys').val(userKeys);
                    m.mount(document.getElementById('logFeed'),
                        m.component(LogFeed.LogFeed,
                                    {node: node, noTarget: noTarget}));
                };
                updateUserKeysForRecentActivity(LogSearchName, updateLog, urlFilesGrid);
            }
        };

        initUserKeysForRecentActivity();

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
                            title: _('Name'),
                            width : '70%',
                            sort : true,
                            sortType : 'text'
                        },
                        {
                            title: _('Modified'),
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
                },
                onload : function () {
                    var tb = this;
                    // Add loading modal when loading page
                    tb.select('#tb-tbody').prepend(
                        '<div style="width: 100%; height: 100%; padding: 50px 100px; position: sticky; top: 0; left: 0; background-color: white;"' +
                        ' class="tb-modal-shade">' +
                        '<div class="spinner-loading-wrapper" style="background-color: transparent;">' +
                        '<div class="ball-scale ball-scale-blue"><div></div></div>' +
                        '<p class="m-t-sm fg-load-message">Loading files...</p>' +
                        '</div></div>'
                    );
                    // Hide loading
                    tb.select('#tb-tbody > .tb-modal-shade').hide();
                    tb.select('#tb-tbody').css('overflow', '');
                    Fangorn.DefaultOptions.onload.call(this);
                }
            };
            var filebrowser = new Fangorn(fangornOpts);
            var newComponentElem = document.getElementById('newComponent');
            if (window.contextVars.node.isPublic) {
                m.mount(
                    document.getElementById('shareButtonsPopover'),
                    m.component(
                        SocialShare.ShareButtonsPopover,
                        {title: window.contextVars.node.title, url: window.location.href, type: 'link'}
                    )
                );
            }
            if (newComponentElem) {
                m.mount(newComponentElem, AddComponentButton);
            }
            return promise;
        }, function(xhr, textStatus, error) {
            Raven.captureMessage(_('Error retrieving filebrowser'), {extra: {url: urlFilesGrid, textStatus: textStatus, error: error}});
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
        defaultText: _('Add a project tag to enhance discoverability'),
        onAddTag: function(tag) {
            $('a[title="Removing tag"]').attr('title', _('Removing tag'));
            $('#node-tags_tag').attr('data-default', _('Add a tag'));
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
                Raven.captureMessage(_('Failed to add tag'), {
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
                    $osf.growl('Error', _('Could not remove tag'));
                    Raven.captureMessage(_('Failed to remove tag'), {
                        extra: {
                            tag: tag, url: tagsApiUrl, textStatus: textStatus, error: error
                        }
                    });
                }
            });
        }
    });

    // allows inital default message to fit on empty tag -> allow all default messages width 300px
    //if(!$('.tag').length){
        $('#node-tags_tag').css('width', '300px');
    //}

    $('#addPointer').on('shown.bs.modal', function(){
        if(!$osf.isIE()){
            $('#addPointer input').focus();
        }
    });

    // Limit the maximum length that you can type when adding a tag
    $('#node-tags_tag').attr('maxlength', '128');
    //i18n
    $('a[title="Removing tag"]').attr('title', _('Removing tag'));

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
            var rawText;
            if(resp.wiki_content){
                rawText = resp.wiki_content;
            } else if(window.contextVars.currentUser.canEdit) {
                rawText = _('*Add important information, links, or images here to describe your project.*');
            } else {
                rawText = _('*No wiki content.*');
            }

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
        $('a[title="' + _('Removing tag') + '"]').remove();
        $('span.tag span').each(function(idx, elm) {
            $(elm).text($(elm).text().replace(/\s*$/, ''));
        });
    }

    // Show or hide collection details
    if ($('.collection-details').length) {
        $('.collection-details').each( function() {
            var caret = '#' + $(this).attr('id') + '-toggle';
            $(this).on('hidden.bs.collapse', function(e) {
                $(caret).removeClass('fa-angle-up')
                       .addClass('fa-angle-down');
            }).on('shown.bs.collapse', function(e) {
                $(caret).removeClass('fa-angle-down')
                        .addClass('fa-angle-up');
            });
        });
    }

    var logSearchChangeOldDict = {};
    var logSearchChange = function (selector) {
        var old = logSearchChangeOldDict[selector];
        var val = $(selector).val();
        if (old !== val) {
            RefreshLog();
        }
        logSearchChangeOldDict[selector] = val;
    };
    var initDatepicker = function (selector) {
        var _event = function () {
            logSearchChange(selector);
        };
        datepicker.mount(selector, null).on('hide', _event);
    };
    initDatepicker('#LogSearchS');
    initDatepicker('#LogSearchE');
});
