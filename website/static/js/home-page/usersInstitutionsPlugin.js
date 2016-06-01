/**
 * Meetings and Conferences
 */

var m = require('mithril');

var UsersInstitutions = {
    view: function(ctrl, args) {
        return m('.p-v-sm',
            m('row',
            args.institutions.map(function(inst){
                return m('a', {href: '/institutions/' + inst.id + '/'},
                    m('img.img-circle', {
                     height: '75px', width: '75px',
                     style: {margin: '3px'},
                     title: inst.name,
                     src: inst.logo_path
                 }));
            })
            )
        );
    }
};


module.exports = UsersInstitutions;
