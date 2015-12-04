/**
 * Parses text to return to the log items
 * Created by cos-caner on 12/4/15.
 * Remeber to embed nodes and user in api call i.e. var url = $osf.apiV2Url('nodes/' + nodeId + '/logs/', { query : { 'embed' : ['nodes', 'user']}});
 */
var m = require('mithril'); // exposes mithril methods, useful for redraw etc.


var logActions = {
    'project_created':  '${user} created ${node} ',
    'project_registered':   '${node} is registered by ${user}',
    'project_deleted':  '${node} is deleted by ${user}',
    'created_from':     '${node} is created using an existing project as a template',
    'pointer_created':  'Link to ${node}is created',
    'pointer_forked':   '{} is forked',
    'pointer_removed':  'Pointer is removed',
    'made_public':  'A ${node} is made public',
    'made_private':     'A ${node} is made private',
    'tag_added':    'A tag is added to a ${node}',
    'tag_removed':  'A tag is removed from a ${node}',
    'edit_title':   'A ${node}\'s title is changed',
    'edit_description':     'A ${node}\'s description is changed',
    'updated_fields':   'One or more of a ${node}\'s fields are changed',
    'external_ids_added':   'An external identifier is added to a ${node} (e.g. DOI, ARK)',
    'contributor_added':    'A Contributor is added to a ${node}',
    'contributor_removed':  'A Contributor is removed from a ${node}',
    'contributors_reordered':   'A Contributor\'s position is a ${node}\'s biliography is changed',
    'permissions_update':   'A Contributor\'s permissions on a ${node} are changed',
    'made_contributor_visible':     'A Contributor is made bibliographically visible on a ${node}',
    'made_contributor_invisible':   'A Contributor is made bibliographically invisible on a ${node}',
    'wiki_updated':     'A ${node}\'s wiki is updated',
    'wiki_deleted':     'A ${node}\'s wiki is deleted',
    'wiki_renamed':     'A ${node}\'s wiki is renamed',
    'made_wiki_public':     'A ${node}\'s wiki is made public',
    'made_wiki_private':    'A ${node}\'s wiki is made private',
    'addon_added':  'An add-on is linked to a ${node}',
    'addon_removed':    'An add-on is unlinked from a ${node}',
    'addon_file_moved':     'A File in a ${node}\'s linked add-on is moved',
    'addon_file_copied':    'A File in a ${node}\'s linked add-on is copied',
    'addon_file_renamed':   'A File in a ${node}\'s linked add-on is renamed',
    'folder_created':   'A Folder is created in a ${node}\'s linked add-on',
    'file_added':   'A File is added to a ${node}\'s linked add-on',
    'file_updated':     'A File is updated on a ${node}\'s linked add-on',
    'file_removed':     'A File is removed from a ${node}\'s linked add-on',
    'file_restored':    'A File is restored in a ${node}\'s linked add-on',
    'comment_added':    'A Comment is added to some item',
    'comment_removed':  'A Comment is removed from some item',
    'comment_updated':  'A Comment is updated on some item',
    'embargo_initiated':    'An embargoed Registration is proposed on a ${node}',
    'embargo_approved':     'A proposed Embargo of a ${node} is approved',
    'embargo_cancelled':    'A proposed Embargo of a ${node} is cancelled',
    'embargo_completed':    'A proposed Embargo of a ${node} is completed',
    'retraction_initiated':     'A Retraction of a Registration is proposed',
    'retraction_approved':  'A Retraction of a Registration is approved',
    'retraction_cancelled':     'A Retraction of a Registration is cancelled',
    'registration_initiated':   'A Registration of a ${node} is proposed',
    'registration_approved':    'A proposed Registration is approved',
    'registration_cancelled':   'A proposed Registration is cancelled',
    'node_created':     'A ${node} is created (deprecated)',
    'node_forked':  'A ${node} is forked (deprecated)',
    'node_removed':  'A ${node} is deleted (deprecated)',
    'osf_storage_file_added' : '${user} added a ${file} to ${node}'
};

var LogText = {
    controller : function (logObject){

    },
    view : function(ctrl, logObject) {
        var text = logActions[logObject.attributes.action];
        var list = text.split(/(\${.*?})/);
        return m('.osf-log-item',[
            list.map(function(piece){
                if(piece === '') { return; }
                if(piece === '${user}') {
                    return m.component(UserLink, logObject.embeds.user);
                }
                if(piece === '${node}'){
                    return m.component(NodeLink, logObject.embeds.nodes);
                }

                return piece;
            })
        ]);

    }
};

var UserLink = {
    view : function(ctrl, userObject){
        console.log(userObject);
        return m('a', { href : userObject.data.links.html}, userObject.data.attributes.full_name);
    }
};

var NodeLink = {
    view : function (ctrl, nodeObject) {
        console.log(nodeObject);
        return m('a', { href : nodeObject.data[0].links.html}, nodeObject.data[0].attributes.title);
    }
};

module.exports = LogText;