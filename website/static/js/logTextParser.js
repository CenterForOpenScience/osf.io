/**
 * Parses text to return to the log items
 * Created by cos-caner on 12/4/15.
 * Remeber to embed nodes and user in api call i.e. var url = $osf.apiV2Url('nodes/' + nodeId + '/logs/', { query : { 'embed' : ['nodes', 'user']}});
 */
var m = require('mithril'); // exposes mithril methods, useful for redraw etc.
var logActions = require('js/logActionsList');

var LogText = {
    controller : function (logObject){
        var self = this;
        self.buildTemplate = function () {   // Build template in controller to run only once
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
        };
        self.finalTemplate = self.buildTemplate();

    },
    view : function(ctrl, logObject) {
        return ctrl.finalTemplate;
    }
};

var LogPieces = {
    // User that took the action
    user: {
        view: function (ctrl, logObject) {
            var userObject = logObject.embeds.user;
            return m('a', {href: userObject.data.links.html}, userObject.data.attributes.full_name);
        }
    },
    // Node involved
    node: {
        view: function (ctrl, logObject) {
            var nodeObject = logObject.embeds.nodes;
            return m('a', {href: nodeObject.data[0].links.html}, nodeObject.data[0].attributes.title);
        }
    },
    // Contrubutor list of added, updated etc.
    contributors: {
        view: function (ctrl, logObject) {
            return m('span', 'Placeholder');
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
            return m('span', 'Placeholder');
        }
    },
    // Node that acted as template to create a new node involved
    template: {
        view: function (ctrl, logObject) {
            return m('span', 'Placeholder');
        }
    },
    // The original title of node involved
    title_original: {
        view: function (ctrl, logObject) {
            return m('span', 'Placeholder');
        }
    },
    // The new title of node involved
    title_new: {
        view: function (ctrl, logObject) {
            return m('span', 'Placeholder');
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