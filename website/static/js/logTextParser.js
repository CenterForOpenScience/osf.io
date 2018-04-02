/**
 * Parses text to return to the log items
 * Created by cos-caner on 12/4/15.
 * Remember to embed original_node, user, linked_node and template_node in api call i.e. var url = $osf.apiV2Url('nodes/' + nodeId + '/logs/', { query : { 'embed' : ['original_node', 'user']}});
 */
var m = require('mithril'); // exposes mithril methods, useful for redraw etc.
var logActions = require('json-loader!js/_allLogTexts.json');
var anonymousLogActions = require('json-loader!js/_anonymousLogTexts.json');
var $ = require('jquery');  // jQuery
var $osf = require('js/osfHelpers');
var Raven = require('raven-js');
var lodashGet = require('lodash.get');

var ravenMessagesCache = []; // Cache messages to avoid sending multiple times in one page view
var nodeCategories = require('json-loader!built/nodeCategories.json');

//Used when calling getContributorList to limit the number of contributors shown in a single log when many are mentioned
var numContributorsShown = 3;

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
        // If the user changed the home page, display logText with capitalized
        // name to reflect how home is displayed to user.
        var type = logObject.attributes.action;
        if (type === 'wiki_updated' && source === 'home') {
            source = 'Home';
        }
        source = $osf.decodeText(source);
        return view_url ? m('a', {href: $osf.toRelativeUrl(view_url, window)}, source) : m('span', source);
    }
    return m('span', text);
};

/**
 * Returns a list of contributors to show in log as well as the trailing punctuation/text after each contributor.
 * If a contributor has a OSF profile, contributor is returned as a mithril link to user.
 * @param contributors {string} The list of contributors (OSF users or unregistered)
 * @param maxShown {int} the number of contributors shown before saying "and # others"
 * Note: if there is only 1 over maxShown, all contributors are shown
 * @returns {array}
 */
var getContributorList = function (contributors, maxShown){
       var contribList = [];
       var justOneMore = numContributorsShown === contributors.length -1;
       for(var i = 0; i < contributors.length; i++){
           var item = contributors[i];
           var comma = ' ';
           if(i !== contributors.length -1 && ((i !== maxShown -1) || justOneMore)){
               comma = ', ';
           }
           if(i === contributors.length -2 || ((i === maxShown -1) && !justOneMore) && (i !== contributors.length -1)) {
               if (contributors.length === 2)
                   comma = ' and ';
               else
                   comma = ', and ';
           }

           if (i === maxShown && !justOneMore){
               contribList.push([((contributors.length - i).toString() + ' others'), ' ']);
               return contribList;
           }

           if (item.active) {
               contribList.push([ m('a', {href: '/' + item.id + '/'}, item.full_name), comma]);
           }
           else {
               if (item.unregistered_name) {
                   contribList.push([item.unregistered_name, comma]);
               } else {
                   contribList.push([item.full_name, comma]);
               }
       }}
       return contribList;
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
                if (logObject.anonymous) {
                    return anonymousLogActions[logObject.attributes.action];
                } else if (text.indexOf('${user}') !== -1) {
                    var userObject = logObject.embeds.user;
                    if (userInfoReturned(userObject)) {
                        return text;
                    }
                    else {
                        var newAction = logObject.attributes.action + '_no_user';
                        return logActions[newAction] ? logActions[newAction]: text;
                    }
                } else {
                    return text;
                }
            }
        return null;
        };
        var message = '';
        var text = logText();
        if(text){
            if (logObject.anonymous) { return m('span.osf-log-item', text); }
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
            message = 'The log viewer has encountered an unexpected log action: ' + logObject.attributes.action +
                '. Please add a new log entry for this action to logActionsList.json' +
                ' and anonymousLogActionsList.json, or, if this log relates to an addon, ' +
                'to {addonName}LogActionList.json and {addonName}AnonymousLogActionList.json';
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
                return m('a', {href: $osf.toRelativeUrl(userObject.data.links.html, window), onclick: function() {
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

            // Log action is node_removed
            if (logObject.attributes.action === 'node_removed') {
                if (logObject.attributes.params.params_node) {
                    return m('span', $osf.decodeText(logObject.attributes.params.params_node.title));
            }}
            else if(paramIsReturned(nodeObject, logObject) && nodeObject.data){
                if (nodeObject.data.links && nodeObject.data.attributes) {
                    return m('a', {href: $osf.toRelativeUrl(nodeObject.data.links.html, window), onclick: function() {
                        $osf.trackClick(logObject.trackingCategory, logObject.trackingAction, 'navigate-to-project-from-logs');
                    }}, $osf.decodeText(nodeObject.data.attributes.title));
                }
                else if (nodeObject.data.attributes) {
                    return m('span', $osf.decodeText(nodeObject.data.attributes.title));
                }
            }
            // Original node has been deleted
            else if (!paramIsReturned(nodeObject, logObject)) {
                var deletedNode = logObject.attributes.params.params_node;
                if (paramIsReturned(deletedNode, logObject)){
                     return m('span', $osf.decodeText(deletedNode.title));
                }
            }
            return m('span', 'a project');
        }
    },

    // Contributor list of added, updated etc.
    contributors: {
        view: function (ctrl, logObject) {
            var contributors = logObject.attributes.params.contributors;
            if(paramIsReturned(contributors, logObject)) {
                return m('span', getContributorList(contributors, numContributorsShown));
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
            var title = $osf.decodeText(forkedFrom.title);
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
            if (linked_node && paramIsReturned(linked_node, logObject) && !linked_node.errors) {
                return m('a', {href: $osf.toRelativeUrl(linked_node.data.links.html, window)}, $osf.decodeText(linked_node.data.attributes.title));
            }
            var linked_registration = logObject.embeds.linked_registration;
            if (linked_registration && paramIsReturned(linked_registration, logObject) && !linked_registration.errors) {
                return m('a', {href: $osf.toRelativeUrl(linked_registration.data.links.html, window)}, $osf.decodeText(linked_registration.data.attributes.title));
            }
            return m('span', 'a project');
        }
    },
    // Pointer category
    pointer_category: {
        view: function (ctrl, logObject) {
            var linked_node = logObject.embeds.linked_node;
            var category = '';
            if (linked_node && paramIsReturned(linked_node, logObject) && !linked_node.errors) {
                category = linked_node.data.attributes.category;
                if (category !== '') {
                    return m('span', linked_node.data.attributes.category);
                }
            }
            var linked_registration = logObject.embeds.linked_registration;
            if (linked_registration && paramIsReturned(linked_registration, logObject) && !linked_registration.errors) {
                category = linked_registration.data.attributes.category;
                if (category !== '') {
                    return m('span', linked_registration.data.attributes.category);
                }
            }
            return m('span', '');
        }
    },
    // Node that acted as template to create a new node involved
    template: {
        view: function (ctrl, logObject) {
            var template_node = logObject.embeds.template_node;

            if(paramIsReturned(template_node, logObject)){
                return m('a', {href: $osf.toRelativeUrl(template_node.data.links.html, window)}, $osf.decodeText(template_node.data.attributes.title));
            }

            var templateFromParams = logObject.attributes.params.template_node;
                if (paramIsReturned(templateFromParams, logObject && templateFromParams.title)){
                    return m('span', $osf.decodeText(templateFromParams.title));
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
            var url = null;
            var nodeObject = logObject.embeds.original_node;

            if (paramIsReturned(nodeObject, logObject && nodeObject.data)){
                url = lodashGet(nodeObject, 'data.links.html', null);
            }
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
                if (doi) {
                    return m('span', 'doi:' + doi);
                }
                if (ark) {
                    return m('span', 'ark:' + ark );
                }
            }
            return m('span', '');
        }
    },
    // Wiki page name
    page: {
        view: function (ctrl, logObject) {
            var url = null;
            var action = logObject.attributes.action;
            var acceptableLinkedItems = ['wiki_updated', 'wiki_renamed'];
            var page_id = logObject.attributes.params.page_id;

            if (acceptableLinkedItems.indexOf(action) !== -1) {
                if (paramIsReturned(page_id, logObject)){
                    url = '/' + page_id;
                }
            }
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
                var sourceMaterialized = stripBackslash(source.materialized);
                return m('span', [sourceMaterialized, ' in ', source.addon]);
            }
            return m('span','a name/location' );
        }
    },
    //
    destination: {
        view: function (ctrl, logObject) {
            var destination = logObject.attributes.params.destination;
            if(paramIsReturned(destination, logObject)){
                var destinationMaterialized = destination.materialized;
                if (destinationMaterialized.endsWith('/')){
                    destinationMaterialized = stripBackslash(destination.materialized);
                    return m('span', [destinationMaterialized, ' in ', destination.addon]);
                }
                return m('span', [m('a', {href: $osf.toRelativeUrl(destination.url, window)}, destinationMaterialized), ' in ', destination.addon]);
            }
            return m('span','a new name/location' );
        }
    },
        //
    kind: {
        view: function (ctrl, logObject) {
            return returnTextParams('kind', '', logObject);
        }
    },
        //
    path: {
        controller: function(logObject){
            var self = this;
            self.returnLinkForPath = function(logObject) {
                if (logObject) {
                    var action = logObject.attributes.action;
                    var acceptableLinkedItems = ['osf_storage_file_added', 'osf_storage_file_updated', 'file_tag_added', 'file_tag_removed',
                    'github_file_added', 'github_file_updated', 'box_file_added', 'box_file_updated', 'dropbox_file_added', 'dropbox_file_updated',
                    's3_file_added', 's3_file_updated', 'figshare_file_added', 'checked_in', 'checked_out'];
                    if (acceptableLinkedItems.indexOf(action) !== -1 && logObject.attributes.params.urls) {
                       return logObject.attributes.params.urls.view;
                    }
                }
                return null;
            };
        },
        view: function (ctrl, logObject) {
            var url = ctrl.returnLinkForPath(logObject);
            return returnTextParams('path', 'a file', logObject, url);
        }
    },
        //
    filename: {
        controller: function(logObject) {
            var self = this;
            self.returnLinkForPath = function(logObject){
                if (logObject){
                    var action = logObject.attributes.action;
                    var acceptableLinkedItems = ['dataverse_file_added'];
                    if (acceptableLinkedItems.indexOf(action) !== -1 && logObject.attributes.params.urls) {
                        return logObject.attributes.params.urls.view;
                    }
                }
                return null;
            };
        },
        view: function (ctrl, logObject) {
            var url = ctrl.returnLinkForPath(logObject);
            return returnTextParams('filename', 'a title', logObject, url);
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

    bitbucket_repo: {
        view: function(ctrl, logObject) {
            var bitbucketUser = logObject.attributes.params.bitbucket_user;
            var bitbucketRepo = logObject.attributes.params.bitbucket_repo;
            if (paramIsReturned(bitbucketRepo, logObject) && paramIsReturned(bitbucketUser, logObject)){
                return m('span', bitbucketUser + '/' + bitbucketRepo);
            }
            return m('span', '');
        }
    },

    folder_name: {
        view: function(ctrl, logObject) {
            return returnTextParams('folder_name', 'a folder', logObject);
        }
    },

    library_name: {
        view: function(ctrl, logObject) {
            return returnTextParams('library_name', 'a library', logObject);
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

    onedrive_folder: {
        view: function(ctrl, logObject) {
            var folder = logObject.attributes.params.folder;

            if(paramIsReturned(folder, logObject)){
                return m('span', folder === '/' ? '/ (Full OneDrive)' : folder);
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
            self.returnLinkForPath = function(logObject) {
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
            var url = ctrl.returnLinkForPath(logObject);
            var path = logObject.attributes.params.path;
            if(paramIsReturned(path, logObject)){
                path = stripBackslash(path);
                if (url) {
                     return m('a', {href: $osf.toRelativeUrl(url, window)}, path);
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
                return m('span', folder === '/' ? '(Full Google Drive)' : folder);
            }
            return m('span', '');
        }
    },

    addon: {
        view: function(ctrl, logObject){
            return returnTextParams('addon', '', logObject);
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

    comment_location: {
        view: function(ctrl,logObject){
            var file = logObject.attributes.params.file;
            var wiki = logObject.attributes.params.wiki;
            // skip param.isReturned as not having a file or wiki is expected at times
            // Comment left on file
            if (file){
                return m('span', ['on ', m('a', {href: $osf.toRelativeUrl(file.url, window)}, file.name)]);
            }
            // Comment left on wiki
            if (wiki) {
                var name = (wiki.name === 'home') ? 'Home' : wiki.name;
                return m('span', ['on wiki page ', m('a', {href: $osf.toRelativeUrl(wiki.url, window)}, name)]);
            }
            // Comment left on project
            return m('span', '');
        }
    },

    preprint: {
        view: function(ctrl, logObject){
            var preprint = logObject.attributes.params.preprint;
            if (paramIsReturned(preprint, logObject)) {
                return m('a', {href: '/' + preprint}, 'preprint');
            }
            return m('span', 'preprint');
        }
    },

    preprint_provider: {
        view: function(ctrl, logObject){
            var preprint_provider = logObject.attributes.params.preprint_provider;
            if (paramIsReturned(preprint_provider, logObject)) {
                return m('a', {href: preprint_provider.url}, preprint_provider.name);
            }
            return m('span', '');
        }
    },

    subjects: {
        view: function(ctrl, logObject){
            var subjects = logObject.attributes.params.subjects;
            if (paramIsReturned(subjects, logObject)) {
                return m('span', subjects.map(function(item) {return item.text;}).join(', '), '');
            }
            return m('span', '');
        }
    },

    license: {
        view: function(ctrl, logObject){
            var license_name = logObject.attributes.params.license;
            if (license_name) {
                return m('span', 'to ' + license_name);
            }
            return m('span', '');
        }
    },

    anonymous_link: {
        view: function(ctrl, logObject) {
            if (logObject.attributes.params.anonymous_link) {
                return m('span', 'an anonymous');
            }
            return m('span', 'a');
        }
    },

    gitlab_repo: {
        view: function(ctrl, logObject){
            var gitlab_user = logObject.attributes.params.gitlab_user;
            var gitlab_repo = logObject.attributes.params.gitlab_repo;
            if (paramIsReturned(gitlab_repo, logObject) && paramIsReturned(gitlab_user, logObject)) {
                return m('span', gitlab_user + '/' + gitlab_repo);
            }
            return m('span', '');
        }
    },
};

module.exports = {
    LogText:LogText,
    getContributorList: getContributorList
};
