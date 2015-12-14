/**
 * Parses text to return to the log items
 * Created by cos-caner on 12/4/15.
 * Remeber to embed nodes, user, linked_node and template_node in api call i.e. var url = $osf.apiV2Url('nodes/' + nodeId + '/logs/', { query : { 'embed' : ['nodes', 'user']}});
 */
var m = require('mithril'); // exposes mithril methods, useful for redraw etc.
var logActions = require('js/logActionsList');
var $ = require('jquery');  // jQuery

/**
 * Checks if the required parameter to complete the log is returned
 * This may intentionally not be returned to make log anonymous
 * @param param {string|number} The parameter to be used
 * @param logObject {Object} the entire log object returned from the api
 * @returns {boolean}
 */
var paramIsReturned = function(param, logObject){
    if(!param){
        var message = 'Expected parameter for Log action ' + logObject.attributes.action + ' was not returned from log api.';
        Raven.captureMessage(message, {logObject: logObject});
        return false;
    }
    return true;
};


/**
 * Returns the text parameters since their formatting is mainly the same
 * @param param {string} The parameter to be used, has to be available under logObject.attributes.param
 * @param text {string'} The text to be used if param is not available
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
                        return m('span', ' and ' + item);
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
        var list = text.split(/(\${.*?})/);
        return m('span.osf-log-item',[
                list.map(function(piece){
                    if(piece === '') { return; }
                    var startsWith = piece.substring(0,2);
                    if(startsWith === '${'){
                        var last = piece.length-1;
                        var logComponentName = piece.substring(2,last);
                        return m.component(LogPieces[logComponentName], logObject);
                    }
                    return piece;
                })
            ]);
    }
};

var LogPieces = {
    // User that took the action
    user: {
        view: function (ctrl, logObject) {
            var userObject = logObject.embeds.user;
            if(paramIsReturned(userObject, logObject)) {
                return m('a', {href: userObject.data.links.html}, userObject.data.attributes.full_name);
            } else {
                return m('span', 'a user');
            }
        }
    },
    // Node involved
    node: {
        view: function (ctrl, logObject) {
            var nodeObject = logObject.embeds.nodes;
            if(paramIsReturned(nodeObject, logObject)){
                return m('a', {href: nodeObject.data[0].links.html}, nodeObject.data[0].attributes.title);
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
                return contributors.map(function(item){
                    return m('a', {href: '#'}, 'Person');
                });
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
                return m('a', {href: source.url}, source.materialized);
            }
            return m('span','a name/location' );
        }
    },
    //
    destination: {
        view: function (ctrl, logObject) {
            var destination = logObject.attributes.params.destination;
            if(paramIsReturned(destination, logObject)){
                return m('a', {href: destination.url}, destination.materialized);
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
        //
    study: {
        view: function (ctrl, logObject) {
            return returnTextParams('study', 'a study', logObject);
        }
    },
        //
    dataset: {
        view: function (ctrl, logObject) {
            return returnTextParams('dataset', 'a dataset', logObject);
        }
    },
};


module.exports = LogText;