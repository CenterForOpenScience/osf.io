/**
 * UI and function to quick search projects
 */

var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');
var nodeModule = require('js/quickProjectSearchPlugin');

// XHR config for apiserver connection
var xhrconfig = function(xhr) {
    xhr.withCredentials = true;
};


var newAndNoteworthy = {
    controller: function() {

    },
    view : function(ctrl) {
        function newProjectsTemplate () {
            return m('h1', 'Node')

        }
        function noteworthyProjectsTemplate() {
            return m('h1', 'Nodes')

        }
        return m('div', {class: 'container'}, [
            m('div', {class: 'row'}, m('div', {class: 'col-sm-12'}, m('h4', 'Discover Public Projects'))),
            m('div', {class: 'row'},
                m('div', {class: 'col-sm-6'}, [m('h5', 'New'), newProjectsTemplate() ]),
                m('div', {class: 'col-sm-6'}, [m('h5', 'Noteworthy', noteworthyProjectsTemplate())])
            )
        ])
    }
};

module.exports = newAndNoteworthy;

