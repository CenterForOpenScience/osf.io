/**
 * Parses text to return to the log items
 * Created by cos-caner on 12/4/15.
 * Remember to embed nodes, user, linked_node and template_node in api call i.e. var url = $osf.apiV2Url('nodes/' + nodeId + '/logs/', { query : { 'embed' : ['nodes', 'user']}});
 */
var m = require('mithril'); // exposes mithril methods, useful for redraw etc.
var logActions = require('json!js/_allLogTexts.json');
var $ = require('jquery');  // jQuery
var $osf = require('js/osfHelpers');

var ravenMessagesCache = []; // Cache messages to avoid sending multiple times in one page view
/**
 * Utility function to not repeat logging errors to Sentry
 * @param message {String} Custom message for error
 * @param logObject {Object} the entire log object returned from the api
 */
function ravenMessage (message, logObject) {
    if(ravenMessagesCache.indexOf(message) === -1){
        Raven.captureMessage(message, {logObject: logObject});
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


/**
 * Returns the text parameters since their formatting is mainly the same
 * @param param {string} The parameter to be used, has to be available under logObject.attributes.param
 * @param text {string} The text to be used if param is not available
 * @param logObject {Object} the entire log object returned from the api
 * @returns {*}
 */
var returnTextParams = function (param, text, logObject) {
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
        return m('span', '"' + source + '"');
    }
    return m('span', text);
};

var LogText = {
    view : function(ctrl, logObject) {
        var text = logActions[logObject.attributes.action];
        var message = '';
        if(text){
            var list = text.split(/(\${.*?})/);
            return m('span.osf-log-item',[
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
            return m('');
        }
    }
};

var LogPieces = {
    // User that took the action
    user: {
        view: function (ctrl, logObject) {
            var userObject = logObject.embeds.user;
            if(paramIsReturned(userObject, logObject) && userObject.data) {
                return m('a', {href: userObject.data.links.html, onclick: function() {
                    $osf.trackClick(logObject.trackingCategory, logObject.trackingAction, 'navigate-to-user-from-logs');
                }}, userObject.data.attributes.full_name);
            } else {
                return m('span', 'A user');
            }
        }
    },
    // Node involved
    node: {
        view: function (ctrl, logObject) {
            var nodeObject = logObject.embeds.nodes;
            if(paramIsReturned(nodeObject, logObject) && nodeObject.data[0]){
                return m('a', {href: nodeObject.data[0].links.html, onclick: function() {
                    $osf.trackClick(logObject.trackingCategory, logObject.trackingAction, 'navigate-to-project-from-logs');
                }}, nodeObject.data[0].attributes.title);
            } else {
                return m('span', 'a project');
            }
        }
    },
    // Contrubutor list of added, updated etc.
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
                    if (item.attributes.active) {
                        return [ m('a', {href: item.links.html}, item.attributes.full_name), comma];
                    }
                    else {
                        return [item.attributes.full_name, comma];

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
            return m('span', 'a tag');
       }
    },
    // Node that is linked to the node involved
    pointer: {
        view: function (ctrl, logObject) {
            var linked_node = logObject.embeds.linked_node;
            if(paramIsReturned(linked_node, logObject)){
                return m('a', {href: linked_node.data.links.html}, linked_node.data.attributes.title);
            }
            return m('span','a project' );
        }
    },
    // Node that acted as template to create a new node involved
    template: {
        view: function (ctrl, logObject) {
            var template_node = logObject.embeds.template_node;
            if(paramIsReturned(template_node, logObject)){
                return m('a', {href: template_node.data.links.html}, template_node.data.attributes.title);
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
        view: function (ctrl, logObject) {
            return returnTextParams('title_new', 'a title', logObject);
        }
    },
    // Update fields for the node
    updated_fields: {
        view: function (ctrl, logObject) {
            return returnTextParams('updated_fields', 'field(s)', logObject);
        }
    },
    // external identifiers on node
    identifiers: {
        view: function (ctrl, logObject) {
            return returnTextParams('identifiers', 'identifier(s)', logObject);
        }
    },
    // Wiki page name
    page: {
        view: function (ctrl, logObject) {
            return returnTextParams('page', 'a title', logObject);
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
        view: function (ctrl, logObject) {
            return returnTextParams('path', 'a file', logObject);
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
            return returnTextParams('forward_url', 'a new URL', logObject);
        }
    },

    box_folder: {
        view: function(ctrl, logObject) {
            var folder = logObject.attributes.params.folder;
            if(paramIsReturned(folder, logObject)){
                return m('span', folder === 'All Files' ? '/ (Full Box)' : (folder || '').replace('All Files',''));
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
        view: function(ctrl, logObject){
            var path = logObject.attributes.params.path;
            if(paramIsReturned(path, logObject)){
                return m('span', decodeURIComponent(path));
            }
            return m('span', '');
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
                return m('span', previous_institution.name);
            }
            return m('span', 'an institution');
        }
    },

    institution: {
        view: function(ctrl, logObject){
            var institution = logObject.attributes.params.institution;
            if (paramIsReturned(institution, logObject)){
                return m('span', institution.name);
            }
            return m('span', 'an institution');
        }
    },

    comment_file: {
        view: function(ctrl,logObject){
            var file = logObject.attributes.params.file;
            if (file){  // skipe paramIsReturned, as not having a file is expected at times
                return m('span', ['in ', m('a', {href: file.url}, file.name)]);
            }
            return m('span', '');
        }
    }
};

module.exports = LogText;
