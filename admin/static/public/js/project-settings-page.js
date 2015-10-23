webpackJsonp([38],{

/***/ 0:
/***/ function(module, exports, __webpack_require__) {

'use strict';

var $ = __webpack_require__(38);
var bootbox = __webpack_require__(138);
var Raven = __webpack_require__(52);
var ko = __webpack_require__(48);

var ProjectSettings = __webpack_require__(405);

var $osf = __webpack_require__(47);
__webpack_require__(406);

var ctx = window.contextVars;

// Initialize treebeard grid for notifications
var ProjectNotifications = __webpack_require__(376);
var $notificationsMsg = $('#configureNotificationsMessage');
var notificationsURL = ctx.node.urls.api  + 'subscriptions/';
// Need check because notifications settings don't exist on registration's settings page
if ($('#grid').length) {
    $.ajax({
        url: notificationsURL,
        type: 'GET',
        dataType: 'json'
    }).done(function(response) {
        new ProjectNotifications(response);
    }).fail(function(xhr, status, error) {
        $notificationsMsg.addClass('text-danger');
        $notificationsMsg.text('Could not retrieve notification settings.');
        Raven.captureMessage('Could not GET notification settings.', {
            url: notificationsURL, status: status, error: error
        });
    });
}

//Initialize treebeard grid for wiki
var ProjectWiki = __webpack_require__(408);
var wikiSettingsURL = ctx.node.urls.api  + 'wiki/settings/';
var $wikiMsg = $('#configureWikiMessage');

if ($('#wgrid').length) {
    $.ajax({
        url: wikiSettingsURL,
        type: 'GET',
        dataType: 'json'
    }).done(function(response) {
        new ProjectWiki(response);
    }).fail(function(xhr, status, error) {
        $wikiMsg.addClass('text-danger');
        $wikiMsg.text('Could not retrieve wiki settings.');
        Raven.captureMessage('Could not GET wiki settings.', {
            url: wikiSettingsURL, status: status, error: error
        });
    });
}

$(document).ready(function() {

    // Apply KO bindings for Node Category Settings
    var categories = [];
    var keys = Object.keys(window.contextVars.nodeCategories);
    for (var i = 0; i < keys.length; i++) {
        categories.push({
            label: window.contextVars.nodeCategories[keys[i]],
            value: keys[i]
        });
    }
    var disableCategory = !window.contextVars.node.parentExists;
    // need check because node category doesn't exist for registrations
    if ($('#nodeCategorySettings').length) {
        var categorySettingsVM = new ProjectSettings.NodeCategorySettings(
            window.contextVars.node.category,
            categories,
            window.contextVars.node.urls.update,
            disableCategory
        );
        $osf.applyBindings(categorySettingsVM, $('#nodeCategorySettings')[0]);
    }

    $('#deleteNode').on('click', function() {
        ProjectSettings.getConfirmationCode(ctx.node.nodeType);
    });

    // TODO: Knockout-ify me
    $('#commentSettings').on('submit', function() {
        var $commentMsg = $('#configureCommentingMessage');

        var $this = $(this);
        var commentLevel = $this.find('input[name="commentLevel"]:checked').val();

        $osf.postJSON(
            ctx.node.urls.api + 'settings/comments/',
            {commentLevel: commentLevel}
        ).done(function() {
            $commentMsg.text('Successfully updated settings.');
            $commentMsg.addClass('text-success');
            if($osf.isSafari()){
                //Safari can't update jquery style change before reloading. So delay is applied here
                setTimeout(function(){window.location.reload();}, 100);
            } else {
                window.location.reload();
            }

        }).fail(function() {
            bootbox.alert({
                message: 'Could not set commenting configuration. Please try again.',
                buttons:{
                    ok:{
                        label:'Close',
                        className:'btn-default'
                    }
                }
            });
        });

        return false;

    });

    var checkedOnLoad = $('#selectAddonsForm input:checked');
    var uncheckedOnLoad = $('#selectAddonsForm input:not(:checked)');

    // Set up submission for addon selection form
    $('#selectAddonsForm').on('submit', function() {

        var formData = {};
        $('#selectAddonsForm').find('input').each(function(idx, elm) {
            var $elm = $(elm);
            formData[$elm.attr('name')] = $elm.is(':checked');
        });
        var msgElm = $(this).find('.addon-settings-message');
        $.ajax({
            url: ctx.node.urls.api + 'settings/addons/',
            data: JSON.stringify(formData),
            type: 'POST',
            contentType: 'application/json',
            dataType: 'json',
            success: function() {
                msgElm.text('Settings updated').fadeIn();
                checkedOnLoad = $('#selectAddonsForm input:checked');
                uncheckedOnLoad = $('#selectAddonsForm input:not(:checked)');
                if($osf.isSafari()){
                    //Safari can't update jquery style change before reloading. So delay is applied here
                    setTimeout(function(){window.location.reload();}, 100);
                } else {
                    window.location.reload();
                }
            }
        });

        return false;

    });

    /* Before closing the page, Check whether the newly checked addon are updated or not */
    $(window).on('beforeunload',function() {
      //new checked items but not updated
      var checked = uncheckedOnLoad.filter('#selectAddonsForm input:checked');
      //new unchecked items but not updated
      var unchecked = checkedOnLoad.filter('#selectAddonsForm input:not(:checked)');

      if(unchecked.length > 0 || checked.length > 0) {
        return 'The changes on addon setting are not submitted!';
      }
    });

    // Show capabilities modal on selecting an addon; unselect if user
    // rejects terms
    $('.addon-select').on('change', function() {
        var that = this,
            $that = $(that);
        if ($that.is(':checked')) {
            var name = $that.attr('name');
            var capabilities = $('#capabilities-' + name).html();
            if (capabilities) {
                bootbox.confirm({
                    message: capabilities,
                    callback: function(result) {
                        if (!result) {
                            $(that).attr('checked', false);
                        }
                    },
                    buttons:{
                        confirm:{
                            label:'Confirm'
                        }
                    }
               });
            }
        }
    });

});




/***/ },

/***/ 376:
/***/ function(module, exports, __webpack_require__) {

'use strict';

var $ = __webpack_require__(38);
var m = __webpack_require__(158);
var Treebeard = __webpack_require__(159);
var $osf = __webpack_require__(47);
var projectSettingsTreebeardBase = __webpack_require__(377);

function expandOnLoad() {
    var tb = this;  // jshint ignore: line
    for (var i = 0; i < tb.treeData.children.length; i++) {
        var parent = tb.treeData.children[i];
        tb.updateFolder(null, parent);
        expandChildren(tb, parent.children);
    }
}

function expandChildren(tb, children) {
    var openParent = false;
    for (var i = 0; i < children.length; i++) {
        var child = children[i];
        var parent = children[i].parent();
        if (child.data.kind === 'event' && child.data.event.notificationType !== 'adopt_parent') {
            openParent = true;
        }
        if (child.children.length > 0) {
            expandChildren(tb, child.children);
        }
    }
    if (openParent) {
        openAncestors(tb, children[0]);
    }
}

function openAncestors (tb, item) {
    var parent = item.parent();
    if(parent && parent.id > 0) {
        tb.updateFolder(null, parent);
        openAncestors(tb, parent);
    }
}

function subscribe(item, notification_type) {
    var id = item.parent().data.node.id;
    var event = item.data.event.title;
    var payload = {
        'id': id,
        'event': event,
        'notification_type': notification_type
    };
    $osf.postJSON(
        '/api/v1/subscriptions/',
        payload
    ).done(function(){
        //'notfiy-success' is to override default class 'success' in treebeard
        item.notify.update('Settings updated', 'notify-success', 1, 2000);
        item.data.event.notificationType = notification_type;
    }).fail(function() {
        item.notify.update('Could not update settings', 'notify-danger', 1, 2000);
    });
}

function displayParentNotificationType(item){
    var notificationTypeDescriptions = {
        'email_transactional': 'Instantly',
        'email_digest': 'Daily',
        'adopt_parent': 'Adopt setting from parent project',
        'none': 'Never'
    };

    if (item.data.event.parent_notification_type) {
        if (item.parent().parent().parent() === undefined) {
            return '(' + notificationTypeDescriptions[item.data.event.parent_notification_type] + ')';
        }
    }
    return '';
}


function ProjectNotifications(data) {

    //  Treebeard version
    var tbOptions = $.extend({}, projectSettingsTreebeardBase.defaults, {
        divID: 'grid',
        filesData: data,
        naturalScrollLimit : 0,
        resolveRows: function notificationResolveRows(item){
            var columns = [];
            var iconcss = '';
            // check if should not get icon
            if(item.children.length < 1 ){
                iconcss = 'tb-no-icon';
            }
            if (item.data.kind === 'heading') {
                if (item.data.children.length === 0) {
                    columns.push({
                        data : 'project',  // Data field name
                        folderIcons : false,
                        filter : true,
                        sortInclude : false,
                        custom : function() {
                            return m('div[style="padding-left:5px"]',
                                        [m ('p', [
                                                m('b', item.data.node.title + ': '),
                                                m('span[class="text-warning"]', ' No configured projects.')]
                                        )]
                            );
                        }
                    });
                } else {
                    columns.push({
                        data : 'project',  // Data field name
                        folderIcons : false,
                        filter : true,
                        sortInclude : false,
                        custom : function() {
                            return m('div[style="padding-left:5px"]',
                                    [m('p',
                                        [m('b', item.data.node.title + ':')]
                                )]
                            );
                        }
                    });
                }
            }
            else if (item.data.kind === 'folder' || item.data.kind === 'node') {
                columns.push({
                    data : 'project',  // Data field name
                    folderIcons : true,
                    filter : true,
                    sortInclude : false,
                    custom : function() {
                        if (item.data.node.url !== '') {
                            return m('a', { href : item.data.node.url, target : '_blank' }, item.data.node.title);
                        } else {
                            return m('span', item.data.node.title);
                        }

                    }
                });
            }
            else if (item.parent().data.kind === 'folder' || item.parent().data.kind === 'heading' && item.data.kind === 'event') {
                columns.push(
                {
                    data : 'project',  // Data field name
                    folderIcons : true,
                    filter : true,
                    css : iconcss,
                    sortInclude : false,
                    custom : function(item, col) {
                        return item.data.event.description;
                    }
                },
                {
                    data : 'notificationType',  // Data field name
                    folderIcons : false,
                    filter : false,
                    custom : function(item, col) {
                        return m('div[style="padding-right:10px"]',
                            [m('select.form-control', {
                                onchange: function(ev) {
                                    subscribe(item, ev.target.value);
                                }},
                                [
                                    m('option', {value: 'none', selected : item.data.event.notificationType === 'none' ? 'selected': ''}, 'Never'),
                                    m('option', {value: 'email_transactional', selected : item.data.event.notificationType === 'email_transactional' ? 'selected': ''}, 'Instantly'),
                                    m('option', {value: 'email_digest', selected : item.data.event.notificationType === 'email_digest' ? 'selected': ''}, 'Daily')
                            ])
                        ]);
                    }
                });
            }
            else {
                columns.push(
                {
                    data : 'project',  // Data field name
                    folderIcons : true,
                    filter : true,
                    css : iconcss,
                    sortInclude : false,
                    custom : function() {
                        return item.data.event.description;

                    }
                },
                {
                    data : 'notificationType',  // Data field name
                    folderIcons : false,
                    filter : false,
                    custom : function() {
                        return  m('div[style="padding-right:10px"]',
                            [m('select.form-control', {
                                onchange: function(ev) {
                                    subscribe(item, ev.target.value);
                                }},
                                [
                                    m('option', {value: 'adopt_parent',
                                                 selected: item.data.event.notificationType === 'adopt_parent' ? 'selected' : ''},
                                                 'Adopt setting from parent project ' + displayParentNotificationType(item)),
                                    m('option', {value: 'none', selected : item.data.event.notificationType === 'none' ? 'selected': ''}, 'Never'),
                                    m('option', {value: 'email_transactional',  selected : item.data.event.notificationType === 'email_transactional' ? 'selected': ''}, 'Instantly'),
                                    m('option', {value: 'email_digest', selected : item.data.event.notificationType === 'email_digest' ? 'selected': ''}, 'Daily')
                            ])
                        ]);
                    }
                });
            }

            return columns;
        }
    });
    var grid = new Treebeard(tbOptions);
    expandOnLoad.call(grid.tbController);
}

module.exports = ProjectNotifications;


/***/ },

/***/ 377:
/***/ function(module, exports, __webpack_require__) {

/**
 * Treebeard base for project settings
 * Currently used for wiki and notification settings
 */

'use strict';

var $ = __webpack_require__(38);
var m = __webpack_require__(158);
var Treebeard = __webpack_require__(159);
var Fangorn = __webpack_require__(186);


function resolveToggle(item) {
    var toggleMinus = m('i.fa.fa-minus', ' '),
        togglePlus = m('i.fa.fa-plus', ' ');

    if (item.children.length > 0) {
        if (item.open) {
            return toggleMinus;
        }
        return togglePlus;
    }
    item.open = true;
    return '';
}

module.exports = {
    defaults: {
        rowHeight : 33,         // user can override or get from .tb-row height
        resolveToggle: resolveToggle,
        paginate : false,       // Whether the applet starts with pagination or not.
        paginateToggle : false, // Show the buttons that allow users to switch between scroll and paginate.
        uploads : false,         // Turns dropzone on/off.
        resolveIcon : Fangorn.Utils.resolveIconView,
        hideColumnTitles: true,
        columnTitles : function columnTitles(item, col) {
            return [
                {
                    title: 'Project',
                    width: '60%',
                    sortType : 'text',
                    sort : false
                },
                {
                    title: 'Editing Toggle',
                    width : '40%',
                    sort : false

                }
            ];
        },
        ontogglefolder : function (item){
            var containerHeight = this.select('#tb-tbody').height();
            this.options.showTotal = Math.floor(containerHeight / this.options.rowHeight) + 1;
            this.redraw();
        },
        sortButtonSelector : {
            up : 'i.fa.fa-chevron-up',
            down : 'i.fa.fa-chevron-down'
        },
        showFilter : false,     // Gives the option to filter by showing the filter box.
        allowMove : false,       // Turn moving on or off.
        hoverClass : '',
        resolveRefreshIcon : function() {
          return m('i.fa.fa-refresh.fa-spin');
        }
    }
};

/***/ },

/***/ 379:
/***/ function(module, exports, __webpack_require__) {

/**
 * ViewModel mixin for displaying form input help messages.
 * Adds message and messageClass observables that can be changed with the
 * changeMessage method.
 */
'use strict';
var ko = __webpack_require__(48);
var oop = __webpack_require__(146);
/** Change the flashed status message */

var ChangeMessageMixin = oop.defclass({
    constructor: function() {
        this.message = ko.observable('');
        this.messageClass = ko.observable('text-info');
    },
    changeMessage: function(text, css, timeout) {
        var self = this;
        if (typeof text === 'function') {
            text = text();
        }
        self.message(text);
        var cssClass = css || 'text-info';
        self.messageClass(cssClass);
        if (timeout) {
            // Reset message after timeout period
            window.setTimeout(function () {
                self.message('');
                self.messageClass('text-info');
            }, timeout);
        }
    },
    resetMessage: function() {
        this.message('');
        this.messageClass('text-info');        
    }
});

module.exports = ChangeMessageMixin;


/***/ },

/***/ 405:
/***/ function(module, exports, __webpack_require__) {

'use strict';

var $ = __webpack_require__(38);
var bootbox = __webpack_require__(138);
var Raven = __webpack_require__(52);
var ko = __webpack_require__(48);
var $osf = __webpack_require__(47);
var oop = __webpack_require__(146);
var ChangeMessageMixin = __webpack_require__(379);

var NodeCategorySettings = oop.extend(
    ChangeMessageMixin,
    {
        constructor: function(category, categories, updateUrl, disabled) {
            this.super.constructor.call(this);

            var self = this;

            self.disabled = disabled || false;
            self.UPDATE_SUCCESS_MESSAGE = 'Category updated successfully';
            self.UPDATE_ERROR_MESSAGE = 'Error updating category, please try again. If the problem persists, email ' +
                '<a href="mailto:support@osf.io">support@osf.io</a>.';
            self.UPDATE_ERROR_MESSAGE_RAVEN = 'Error updating Node.category';

            self.INSTANTIATION_ERROR_MESSAGE = 'Trying to instantiate NodeCategorySettings view model without an update URL';

            self.MESSAGE_SUCCESS_CLASS = 'text-success';
            self.MESSAGE_ERROR_CLASS = 'text-danger';

            if (!updateUrl) {
                throw new Error(self.INSTANTIATION_ERROR_MESSAGE);
            }

            self.categories = categories;
            self.category = ko.observable(category);
            self.updateUrl = updateUrl;

            self.selectedCategory = ko.observable(category);
            self.dirty = ko.observable(false);
            self.selectedCategory.subscribe(function(value) {
                if (value !== self.category()) {
                    self.dirty(true);
                }
            });
        },
        updateSuccess: function(newcategory) {
            var self = this;
            self.changeMessage(self.UPDATE_SUCCESS_MESSAGE, self.MESSAGE_SUCCESS_CLASS);
            self.category(newcategory);
            self.dirty(false);
        },
        updateError: function(xhr, status, error) {
            var self = this;
            self.changeMessage(self.UPDATE_ERROR_MESSAGE, self.MESSAGE_ERROR_CLASS);
            Raven.captureMessage(self.UPDATE_ERROR_MESSAGE_RAVEN, {
                url: self.updateUrl,
                textStatus: status,
                err: error
            });
        },
        updateCategory: function() {
            var self = this;
            return $osf.putJSON(self.updateUrl, {
                    category: self.selectedCategory()
                })
                .then(function(response) {
                    return response.updated_fields.category;
                })
                .done(self.updateSuccess.bind(self))
                .fail(self.updateError.bind(self));
        },
        cancelUpdateCategory: function() {
            var self = this;
            self.selectedCategory(self.category());
            self.dirty(false);
            self.resetMessage();
        }
    });

var ProjectSettings = {
    NodeCategorySettings: NodeCategorySettings
};

// TODO: Pass this in as an argument rather than relying on global contextVars
var nodeApiUrl = window.contextVars.node.urls.api;


// Request the first 5 contributors, for display in the deletion modal
var contribs = [];
var moreContribs = 0;

var contribURL = nodeApiUrl + 'get_contributors/?limit=5';
var request = $.ajax({
    url: contribURL,
    type: 'get',
    dataType: 'json'
});
request.done(function(response) {
    // TODO: Remove reliance on contextVars
    var currentUserName = window.contextVars.currentUser.fullname;
    contribs = response.contributors.filter(function(contrib) {
        return contrib.shortname !== currentUserName;
    });
    moreContribs = response.more;
});
request.fail(function(xhr, textStatus, err) {
    Raven.captureMessage('Error requesting contributors', {
        url: contribURL,
        textStatus: textStatus,
        err: err,
    });
});


/**
 * Pulls a random name from the scientist list to use as confirmation string
 *  Ignores case and whitespace
 */
ProjectSettings.getConfirmationCode = function(nodeType) {

    // It's possible that the XHR request for contributors has not finished before getting to this
    // point; only construct the HTML for the list of contributors if the contribs list is populated
    var message = '<p>It will no longer be available to other contributors on the project.';

    $osf.confirmDangerousAction({
        title: 'Are you sure you want to delete this ' + nodeType + '?',
        message: message,
        callback: function () {
            var request = $.ajax({
                type: 'DELETE',
                dataType: 'json',
                url: nodeApiUrl
            });
            request.done(function(response) {
                // Redirect to either the parent project or the dashboard
                window.location.href = response.url;
            });
            request.fail($osf.handleJSONError);
        },
        buttons: {
            success: {
                label: 'Delete'
            }
        }
    });
};

module.exports = ProjectSettings;


/***/ },

/***/ 406:
/***/ function(module, exports, __webpack_require__) {

// style-loader: Adds some css to the DOM by adding a <style> tag

// load the styles
var content = __webpack_require__(407);
if(typeof content === 'string') content = [[module.id, content, '']];
// add the styles to the DOM
var update = __webpack_require__(19)(content, {});
// Hot Module Replacement
if(false) {
	// When the styles change, update the <style> tags
	module.hot.accept("!!/Users/laurenbarker/GitHub/osf.io/node_modules/css-loader/index.js!/Users/laurenbarker/GitHub/osf.io/website/static/css/addonsettings.css", function() {
		var newContent = require("!!/Users/laurenbarker/GitHub/osf.io/node_modules/css-loader/index.js!/Users/laurenbarker/GitHub/osf.io/website/static/css/addonsettings.css");
		if(typeof newContent === 'string') newContent = [[module.id, newContent, '']];
		update(newContent);
	});
	// When the module is disposed, remove the <style> tags
	module.hot.dispose(function() { update(); });
}

/***/ },

/***/ 407:
/***/ function(module, exports, __webpack_require__) {

exports = module.exports = __webpack_require__(16)();
exports.push([module.id, ".filebrowser #tb-tbody {\n    height: 300px;\n}\n\n.addon-icon {\n    width: 20px;\n    margin-top: -2px;\n}", ""]);

/***/ },

/***/ 408:
/***/ function(module, exports, __webpack_require__) {

'use strict';

var $ = __webpack_require__(38);
var bootbox = __webpack_require__(138);
var m = __webpack_require__(158);
var Treebeard = __webpack_require__(159);
var $osf = __webpack_require__(47);
var projectSettingsTreebeardBase = __webpack_require__(377);

function expandOnLoad() {
    var tb = this;  // jshint ignore: line
    for (var i = 0; i < tb.treeData.children.length; i++) {
        var parent = tb.treeData.children[i];
        tb.updateFolder(null, parent);
    }
}

function beforeChangePermissions(item, permission){
    var title = item.parent().data.node.title;
    if(permission === 'public'){
        bootbox.dialog({
            title: 'Make publicly editable',
            message: 'Are you sure you want to make the wiki of <b>' +title+
                '</b> publicly editable? This will allow any logged in user to edit the content of this wiki. ' +
                '<b>Note</b>: Users without write access will not be able to add, delete, or rename pages.',
            buttons: {
                cancel : {
                    label : 'Cancel',
                    className : 'btn-default',
                    callback : function() {item.notify.update('', 'notify-primary', 1, 10);}
                },
                success: {
                    label: 'Apply',
                    className: 'btn-primary',
                    callback: function() {changePermissions(item, permission);}
                }
            }
        });
    }
    else {
        changePermissions(item, permission);
    }
}

function changePermissions(item, permission) {
    var id = item.parent().data.node.id;

    return $osf.putJSON(
        buildPermissionsURL(item), {'permission': permission}
    ).done(function(){
        item.notify.update('Settings updated', 'notify-success', 1, 2000);
        item.data.select.permission = permission;
    }).fail(function() {
        item.notify.update('Could not update settings', 'notify-danger', 1, 2000);
    });
}

// Helper to build path
function buildPermissionsURL(item) {
    var id = item.parent().data.node.id;
    var permissionsChangePath = '/api/v1/project/'+ id +
        '/wiki/settings/';
    return permissionsChangePath;
}

function ProjectWiki(data) {

    //  Treebeard version
    var tbOptions = $.extend({}, projectSettingsTreebeardBase.defaults, {
        filesData: data,
        divID: 'wgrid',
        resolveRows: function wikiResolveRows(item){
            var columns = [];
            var iconcss = '';
            // check if should not get icon
            if(item.children.length < 1 ){
                iconcss = 'tb-no-icon';
            }
            if (item.data.kind === 'folder' || item.data.kind === 'node') {
                columns.push({
                    data : 'project',  // Data field name
                    folderIcons : true,
                    filter : true,
                    sortInclude : false,
                    custom : function() {
                        if (item.data.node.url !== '') {
                            return m('a', { href : item.data.node.url, target : '_blank' }, item.data.node.title);
                        } else {
                            return m('span', item.data.node.title);
                        }

                    }
                });
            }

            else {
                columns.push(
                {
                    data : 'project',  // Data field name
                    folderIcons : true,
                    filter : true,
                    css : iconcss,
                    sortInclude : false,
                    custom : function() {
                        return 'Who can edit';
                    }
                },
                {
                    data : 'permission',  // Data field name
                    folderIcons : false,
                    filter : false,
                    custom : function() {
                        return  m('div[style="padding-right:10px"]',
                            [m('select.form-control', {
                                onchange: function(ev) {
                                    beforeChangePermissions(item, ev.target.value);
                                }},
                                [
                                    m('option', {value: 'private', selected : item.data.select.permission === 'public' ? 'selected': ''}, 'Contributors (with write access)'),
                                    m('option', {value: 'public', selected : item.data.select.permission === 'public' ? 'selected': '' }, 'All OSF users')
                            ])
                        ]);
                    }
                });
            }

            return columns;
        }
    });
    var wgrid = new Treebeard(tbOptions);
    expandOnLoad.call(wgrid.tbController);
}

module.exports = ProjectWiki;


/***/ }

});
//# sourceMappingURL=project-settings-page.js.map