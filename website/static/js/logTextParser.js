/**
 * Parses text to return to the log items
 * Created by cos-caner on 12/4/15.
 * Remeber to embed nodes, user, linked_node and template_node in api call i.e. var url = $osf.apiV2Url('nodes/' + nodeId + '/logs/', { query : { 'embed' : ['nodes', 'user']}});
 */
var m = require('mithril'); // exposes mithril methods, useful for redraw etc.
var logActions = require('js/logActionsList');

var paramIsReturned = function(param, logObject){
    if(!param){
        var message = 'Expected parameter ' + param + ' for Log action ' + logObject.attributes.action + ' was not returned from log api.';
        console.error(message);
        Raven.captureMessage(message, {logObject: logObject});
        return false;
    }
    return true;
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
            return m('a', {href: '/search/?q=%22' + logObject.attributes.params.tag + '%22'}, logObject.attributes.params.tag);
        }
    },
    // Node that is linked to the node involved
    pointer: {
        view: function (ctrl, logObject) {
            var linked_node = logObject.embeds.linked_node;
            if(linked_node){
                return m('a', {href: linked_node.data.links.html}, linked_node.data.attributes.title);
            }
            return m('span','a project' );
        }
    },
    // Node that acted as template to create a new node involved
    template: {
        view: function (ctrl, logObject) {
            var template_node = logObject.embeds.template_node;
            if(template_node){
                return m('a', {href: template_node.data.links.html}, template_node.data.attributes.title);
            }
            return m('span','a project' );
        }
    },
    // The original title of node involved
    title_original: {
        view: function (ctrl, logObject) {
            var title_original = logObject.attributes.params.title_original;
            if(title_original){
                return m('span', '"' + title_original + '"');
            }
            return m('span', 'a title');
        }
    },
    // The new title of node involved
    title_new: {
        view: function (ctrl, logObject) {
            var title_new = logObject.attributes.params.title_new;
            if(title_new){
                return m('span', '"' + title_new + '"');
            }
            return m('span', 'a title');
        }
    },
    // Update fields for the node
    updated_fields: {
        view: function (ctrl, logObject) {
            return m('span', 'Placeholder');
        }
    },
    // external identifiers on node
    identifiers: {
        view: function (ctrl, logObject) {
            return m('span', 'Placeholder');
        }
    },
    // Wiki page name
    page: {
        view: function (ctrl, logObject) {
            return m('span', 'Placeholder');
        }
    },
    // Old wiki title that's renamed
    old_page: {
        view: function (ctrl, logObject) {
            return m('span', 'Placeholder');
        }
    },
    // Wiki page version
    version: {
        view: function (ctrl, logObject) {
            return m('span', 'Placeholder');
        }
    },
    //
    source: {
        view: function (ctrl, logObject) {
            return m('span', 'Placeholder');
        }
    },
    //
    destination: {
        view: function (ctrl, logObject) {
            return m('span', 'Placeholder');
        }
    },
        //
    path: {
        view: function (ctrl, logObject) {
            return m('span', 'Placeholder');
        }
    },
        //
    filename: {
        view: function (ctrl, logObject) {
            return m('span', 'Placeholder');
        }
    },
        //
    study: {
        view: function (ctrl, logObject) {
            return m('span', 'Placeholder');
        }
    },
        //
    dataset: {
        view: function (ctrl, logObject) {
            return m('span', 'Placeholder');
        }
    },
};


module.exports = LogText;