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
            return m('.osf-log-item',[
                list.map(function(piece){
                    if(piece === '') { return; }
                    if(piece === '${user}' && logObject.embeds.user) {
                        return m.component(UserLink, logObject.embeds.user);
                    }
                    if(piece === '${node}' && logObject.embeds.nodes){
                        return m.component(NodeLink, logObject.embeds.nodes);
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

var UserLink = {
    view : function(ctrl, userObject){
        return m('a', { href : userObject.data.links.html}, userObject.data.attributes.full_name);
    }
};

var NodeLink = {
    view : function (ctrl, nodeObject) {
        return m('a', { href : nodeObject.data[0].links.html}, nodeObject.data[0].attributes.title);
    }
};

module.exports = LogText;