/**
 * Parses text to return to the log items
 * Created by cos-caner on 12/4/15.
 * Remember to embed original_node, user, linked_node and template_node in api call i.e. var url = $osf.apiV2Url('nodes/' + nodeId + '/logs/', { query : { 'embed' : ['original_node', 'user']}});
 */
var m = require('mithril'); // exposes mithril methods, useful for redraw etc.
var logActions = require('json!js/_allLogTexts.json');
var $ = require('jquery');  // jQuery
var $osf = require('js/osfHelpers');
var Raven = require('raven-js');

var ravenMessagesCache = []; // Cache messages to avoid sending multiple times in one page view
var nodeCategories = require('json!built/nodeCategories.json');
/**
 * Utility function to not repeat logging errors to Sentry
 * @param message {String} Custom message for error
 * @param logObject {Object} the entire log object returned from the api
 */
function ravenMessage (message, logObject) {
    if(ravenMessagesCache.indexOf(message) === -1){
        Raven.captureMessage(message, {extra: {logObject: logObject}});
        ravenMessagesCache.push(message);
    }
}


/**
 * Checks if the required parameter to complete the log is returned
 * This may intentionally not be returned to make log anonymous
 * @param param {string|number} The parameter to be used
 * @param logObject {Object} the entire log object returned from the api
 * @returns {boolean}
 */
var paramIsReturned = function _paramIsReturned (param, logObject){
    if(!param){
        var message = 'Expected parameter for Log action ' + logObject.attributes.action + ' was not returned from log api.';
        ravenMessage(message, logObject);
        return false;
    }
    if (param.errors){
        return false;
    }
    return true;
};

var stripBackslash = function _stripBackslash(path){
    if (path.charAt(0) === '/') {
        path = path.substr(1, path.length - 1);
    }

    if (path.charAt(path.length - 1) === '/') {
        path = path.substr(0, path.length - 1);
    }
    return path;
};

/**
 * Returns the text parameters since their formatting is mainly the same
 * @param param {string} The parameter to be used, has to be available under logObject.attributes.param
 * @param text {string} The text to be used if param is not available
 * @param logObject {Object} the entire log object returned from the api
 * @returns {*}
 */
var returnTextParams = function (param, text, logObject, view_url) {
    var source = logObject.attributes.params[param];

    if(paramIsReturned(source, logObject)){
        if($.isArray(source)){
            return m('span', [
                source.map(function(item, index, arr){
                    if(arr.length === 1 && index === 0){
                        return m('span', item);
                    }
                    if(index === arr.length-1) {
                        return m('span', ', and ' + item);
                    }
                    return m('span', item + ', ');
                })
            ]);
        }
        if (param === 'path'){
            source = stripBackslash(source);
        }
        return view_url ? m('a', {href: view_url}, source) : m('span', source);
    }
    return m('span', text);
};

var LogText = {
    view : function(ctrl, logObject) {
        var userInfoReturned = function(userObject){
            if (userObject){
                if (userObject.data){
                    return true;
                }
                else if (userObject.errors[0].meta){
                    return true;
                }
            }
            return false;
        };
        var logText = function() {
            var text = logActions[logObject.attributes.action];
            if (text) {
                if (text.indexOf('${user}') !== -1) {
                    var userObject = logObject.embeds.user;
                    if (userInfoReturned(userObject)) {
                        return text;
                    }
                    else {
                        var newAction = logObject.attributes.action + '_no_user';
                        return logActions[newAction] ? logActions[newAction]: text;
                    }
                }
                return text;
            }
        return null;
        };
        var message = '';
        var text = logText();
        if(text){
            var list = text.split(/(\${.*?})/);
            return m('span.osf-log-item', [
                list.map(function(piece){
                    if (piece === '') {
                        return m('span');
                    }
                    var startsWith = piece.substring(0,2);
                    if(startsWith === '${'){
                        var last = piece.length-1;
                        var logComponentName = piece.substring(2,last);
                        if(LogPieces[logComponentName]){
                            return m.component(LogPieces[logComponentName], logObject);
                        } else {
                            message = 'There is no template in logTextParser.js for  ' + logComponentName + '.';
                            ravenMessage(message, logObject);
                            return m('');
                        }
                    }
                    return piece;
                })
            ]);
        } else {
            message = 'There is no text entry in dictionary for the action :' + logObject.attributes.action;
            ravenMessage(message, logObject);
            return m('em', 'Unable to retrieve log details');
        }
    }
};

var LogPieces = {
    // User that took the action
    user: {
        view: function (ctrl, logObject) {
            var userObject = logObject.embeds.user;
            var githubUser = logObject.attributes.params.github_user;
            if(paramIsReturned(userObject, logObject) && userObject.data) {
                return m('a', {href: userObject.data.links.html, onclick: function() {
                    $osf.trackClick(logObject.trackingCategory, logObject.trackingAction, 'navigate-to-user-from-logs');
                }}, userObject.data.attributes.full_name);
            }
            else if (userObject && userObject.errors[0].meta) {
                return m('span', userObject.errors[0].meta.full_name);
            }
            else if (githubUser){ //paramIsReturned skipped b/c this is applicable in only a few situtations
                return m('span', githubUser);
            }
            else {
                return m('span', 'A user');
            }
        }
    },
    // Node involved
    node: {
        view: function (ctrl, logObject) {
            var nodeObject = logObject.embeds.original_node;

            // For logs that are returning deleted nodes
            if (nodeObject.data.length === 0){
                var deletedNode = logObject.attributes.params.params_node;
                if (paramIsReturned(deletedNode, logObject)){
                     return m('span', deletedNode.title);
                }
            }
            if (logObject.attributes.action === 'node_removed') {
                if (logObject.attributes.params.params_node) {
                    return m('span', logObject.attributes.params.params_node.title);
            }}
            else if(paramIsReturned(nodeObject, logObject) && nodeObject.data){
                if (nodeObject.data.links && nodeObject.data.attributes) {
                    return m('a', {href: nodeObject.data.links.html, onclick: function() {
                        $osf.trackClick(logObject.trackingCategory, logObject.trackingAction, 'navigate-to-project-from-logs');
                    }}, nodeObject.data.attributes.title);
                }
                else if (nodeObject.data.attributes) {
                    return m('span', nodeObject.data.attributes.title);
                }
            } else {
                return m('span', 'a project');
            }
        }
    },

    // Contributor list of added, updated etc.
    contributors: {
        view: function (ctrl, logObject) {
            var contributors = logObject.embeds.contributors;
            if(paramIsReturned(contributors, logObject)) {
                return m('span', contributors.data.map(function(item, index, arr){
                    var comma = ' ';
                    if(index !== arr.length - 1){
                        comma = ', ';
                    }
                    if(index === arr.length-2){
                        comma = ' and ';
                    }


                    var attributes = item.attributes;
                    if (attributes == null && item.data && item.data.attributes) {
                        attributes = item.data.attributes;
                    }

                    var links = item.links;
                    if (links == null && item.data && item.data.links){
                        links = item.data.links;
                    }

                    if (attributes) {
                        if (attributes.active && links) {
                            return [ m('a', {href: links.html}, attributes.full_name), comma];
                        }
                        else {
                            return [attributes.full_name, comma];
                        }
                    }
                }));
            }
            return m('span', 'some users');
        }
    },
    // The tag added to item involved
    tag: {
        view: function (ctrl, logObject) {
            var tag = logObject.attributes.params.tag;
            if(paramIsReturned(tag, logObject)) {
               return m('a', {href: '/search/?q=%22' + tag + '%22'}, tag);
            }
            return m('span', '');
       }
    },
    // Original node
    forked_from: {
        view: function(ctrl, logObject) {
            var forkedFrom = logObject.attributes.params.params_node;
            var id = forkedFrom.id;
            var title = forkedFrom.title;
            if (paramIsReturned(forkedFrom, logObject) && title){
                if (id) {
                    return m('a', {href: '/' + id + '/' }, title);
                }
                return m('span', title);
            }
            return m('span', 'a project');
        }
    },
    // Node that is linked to the node involved
    pointer: {
        view: function (ctrl, logObject) {
            var linked_node = logObject.embeds.linked_node;
            if(paramIsReturned(linked_node, logObject)){
                return m('a', {href: linked_node.data.links.html}, linked_node.data.attributes.title);
            }
            // Applicable when pointer has been deleted
            var pointer_info = logObject.attributes.params.pointer;
            if (paramIsReturned(pointer_info, logObject)) {
                return m('span', pointer_info.title);
            }
            return m('span','a project');
        }
    },
    // Pointer category
    pointer_category: {
        view: function (ctrl, logObject) {
            var linked_node = logObject.embeds.linked_node;
            if(paramIsReturned(linked_node, logObject)){
                var category = linked_node.data.attributes.category;
                if (category !== '') {
                    return m('span', linked_node.data.attributes.category);
                }
            }

            var linkedNodeParams = logObject.attributes.params.pointer;
            if (paramIsReturned(linkedNodeParams, logObject)) {
                if (linkedNodeParams.category !== '') {
                     return m('span', linkedNodeParams.category);
                }

            }
            return m('span','project');
        }
    },
    // Node that acted as template to create a new node involved
    template: {
        view: function (ctrl, logObject) {
            var template_node = logObject.embeds.template_node;

            if(paramIsReturned(template_node, logObject)){
                return m('a', {href: template_node.data.links.html}, template_node.data.attributes.title);
            }

            var templateFromParams = logObject.attributes.params.template_node;
                if (paramIsReturned(templateFromParams, logObject && templateFromParams.title)){
                     return m('span', templateFromParams.title);
                }
            return m('span','a project' );
        }
    },
    // The original title of node involved
    title_original: {
        view: function (ctrl, logObject) {
            return returnTextParams('title_original', 'a title', logObject);
        }
    },
    // The new title of node involved
    title_new: {
        controller: function(logObject){
            var self = this;
            var nodeObject = logObject.embeds.nodes;

            self.returnLinkForPath = function(){
                if(paramIsReturned(nodeObject, logObject) && nodeObject.data[0]){
                    if (nodeObject.data[0].links && nodeObject.data[0].attributes) {
                        return nodeObject.data[0].links.html;
                    }
                }
                return null;
            };
        },
        view: function (ctrl, logObject) {
            var url = ctrl.returnLinkForPath();
            return returnTextParams('title_new', 'a title', logObject, url);
        }
    },
    // Update fields for the node
    updated_fields: {
        view: function (ctrl, logObject) {
            var updatedFieldsParam = logObject.attributes.params.updated_fields;
            if (paramIsReturned(updatedFieldsParam, logObject)) {
                var updatedField = Object.keys(updatedFieldsParam)[0];
                if (updatedField === 'category'){
                    return m('span', updatedField + ' to ' + nodeCategories[updatedFieldsParam[updatedField].new]);
                }
                return m('span', updatedField + ' to ' + updatedFieldsParam[updatedField].new);
                }
            return m('span', 'field');
        }},
    // external identifiers on node
    identifiers: {
        view: function (ctrl, logObject) {
            external_ids = logObject.attributes.params.identifiers;
            if (paramIsReturned(external_ids, logObject)) {
                var doi = external_ids.doi;
                var ark = external_ids.ark;
                if (doi && ark) {
                    return m('span', 'doi:' + doi + ' and ark:' + ark);
                }
            }
            return m('span', '');
        }
    },
    // Wiki page name
    page: {
        controller: function(logObject){
            var self = this;
            self.action = logObject.attributes.action;
            self.acceptableLinkedItems = ['wiki_updated', 'wiki_renamed'];
            self.page_id = logObject.attributes.params.page_id;

            self.returnLinkForPath = function() {
                if (self.acceptableLinkedItems.indexOf(self.action) !== -1) {
                    if (paramIsReturned(self.page_id, logObject)){
                        return '/' + self.page_id;
                    }
                }
                return null;
            };
        },
        view: function (ctrl, logObject) {
            var url = ctrl.returnLinkForPath();
            return returnTextParams('page', 'a title', logObject, url);
        }
    },
    // Old wiki title that's renamed
    old_page: {
        view: function (ctrl, logObject) {
            return returnTextParams('old_page', 'a title', logObject);
        }
    },
    // Wiki page version
    version: {
        view: function (ctrl, logObject) {
            var version = logObject.attributes.params.version;
            if(paramIsReturned(version, logObject)){
                return m('span', version);
            }
            return m('span', '#');
        }
    },
    //
    source: {
        view: function (ctrl, logObject) {
            var source = logObject.attributes.params.source;
            if(paramIsReturned(source, logObject)){
                return m('span', [source.materialized, ' in ', source.addon]);
            }
            return m('span','a name/location' );
        }
    },
    //
    destination: {
        view: function (ctrl, logObject) {
            var destination = logObject.attributes.params.destination;
            if(paramIsReturned(destination, logObject)){
                if (destination.materialized.endsWith('/')){
                    return m('span', [destination.materialized, ' in ', destination.addon]);
                }
                return m('span', [m('a', {href: destination.url}, destination.materialized), ' in ', destination.addon]);
            }
            return m('span','a new name/location' );
        }
    },
        //
    path: {
        controller: function(logObject){
            var self = this;
            self.returnLinkForPath = function() {
                if (logObject) {
                    var action = logObject.attributes.action;
                    var acceptableLinkedItems = ['osf_storage_file_added', 'osf_storage_file_updated', 'file_tag_added', 'file_tag_removed',
                    'github_file_added', 'github_file_updated', 'box_file_added', 'box_file_updated', 'dropbox_file_added', 'dropbox_file_updated'];
                    if (acceptableLinkedItems.indexOf(action) !== -1 && logObject.attributes.params.urls) {
                         return logObject.attributes.params.urls.view;
                    }
                }
                return null;
            };
        },
        view: function (ctrl, logObject) {
            var url = ctrl.returnLinkForPath();
            return returnTextParams('path', 'a file', logObject, url);
        }
    },
        //
    filename: {
        view: function (ctrl, logObject) {
            return returnTextParams('filename', 'a title', logObject);
        }
    },

    folder: {
        view: function(ctrl, logObject) {
            return returnTextParams('folder', 'a folder', logObject);
        }
    },

    repo: {
        view: function(ctrl, logObject) {
            var github_user = logObject.attributes.params.github_user;
            var github_repo = logObject.attributes.params.github_repo;
            if (paramIsReturned(github_repo, logObject) && paramIsReturned(github_user, logObject)){
                return m('span', github_user + '/' + github_repo);
            }
            return m('span', '');
        }
    },

    folder_name: {
        view: function(ctrl, logObject) {
            return returnTextParams('folder_name', 'a folder', logObject);
        }
    },

    bucket: {
        view: function(ctrl, logObject) {
            return returnTextParams('bucket', 'a bucket', logObject);
        }
    },

    forward_url: {
        view: function(ctrl, logObject) {
            var url = logObject.attributes.params.forward_url;
            return returnTextParams('forward_url', 'a new URL', logObject, url);
        }
    },

    box_folder: {
        view: function(ctrl, logObject) {
            var folder = logObject.attributes.params.folder_name;

            if(paramIsReturned(folder, logObject)){
                return m('span', folder === 'All Files' ? '/ (Full Box)' : folder);
            }
            return m('span', '');
        }
    },

    dropbox_folder: {
        view: function(ctrl, logObject) {
            var folder = logObject.attributes.params.folder;

            if(paramIsReturned(folder, logObject)){
                return m('span', folder === '/' ? '/ (Full Dropbox)' : folder);
            }
            return m('span', '');
        }
    },

    citation: {
        view: function(ctrl, logObject) {
            return returnTextParams('citation_name', '', logObject);
        }
    },

    dataset: {
        view: function(ctrl, logObject){
            return returnTextParams('data_set', '', logObject);
        }
    },

    study: {
        view: function(ctrl, logObject){
            return returnTextParams('study', '', logObject);
        }
    },

    googledrive_path: {
        controller: function(logObject){
            var self = this;
            self.returnLinkForPath = function() {
                if (logObject) {
                    var action = logObject.attributes.action;
                    var acceptableLinkedItems = ['googledrive_file_added', 'googledrive_file_updated'];
                    if (acceptableLinkedItems.indexOf(action) !== -1 && logObject.attributes.params.urls) {
                         return logObject.attributes.params.urls.view;
                    }
                }
                return null;
            };
        },
        view: function (ctrl, logObject) {
            var url = ctrl.returnLinkForPath();
            var path = logObject.attributes.params.path;
            if(paramIsReturned(path, logObject)){
                path = stripBackslash(decodeURIComponent(path));
                if (url) {
                     return m('a', {href: url}, path);
                }
                return m('span', path);
            }
            return m('span', '');
        }
    },

    path_type: {
        view: function(ctrl, logObject){
            var path = logObject.attributes.params.path;
            if (paramIsReturned(path, logObject)) {
                if (path.slice(-1) === '/') {
                    return m('span', 'folder');
                }
            }
            return m('span', 'file');
        }
    },

    googledrive_folder: {
        view: function(ctrl, logObject){
            var folder = logObject.attributes.params.folder;
            if(paramIsReturned(folder, logObject)){
                return m('span', folder === '/' ? '(Full Google Drive)' : decodeURIComponent(folder));
            }
            return m('span', '');
        }
    },

    addon: {
        view: function(ctrl, logObject){
            return returnTextParams('addon', '', logObject);
        }
    },

    previous_institution: {
        view: function(ctrl, logObject){
            var previous_institution = logObject.attributes.params.previous_institution;
            if (paramIsReturned(previous_institution, logObject)){
                if (previous_institution.id !== null) {
                    return m('a', {'href': '/institutions/' + previous_institution.id + '/'}, previous_institution.name);
                }
                return m('span', previous_institution.name);
            }
            return m('span', 'an institution');
        }
    },

    institution: {
        view: function(ctrl, logObject){
            var institution = logObject.attributes.params.institution;
            if (paramIsReturned(institution, logObject)){
                if (institution.id !== null) {
                    return m('a', {'href': '/institutions/' + institution.id + '/'}, institution.name);
                }
                return m('span', institution.name);

            }
            return m('span', 'an institution');
        }
    },

    comment_file: {
        view: function(ctrl,logObject){
            var file = logObject.attributes.params.file;
            if (file){ // skip param.isReturned as not having a file is expected at times
                return m('span', ['on ', m('a', {href: file.url}, file.name)]);
            }
            return m('span', '');
        }
    }
};

module.exports = LogText;
