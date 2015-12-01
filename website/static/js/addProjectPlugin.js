/**
 * UI and function to add project
 */
'use strict';

var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');


var AddProject = {
    controller : function (options) {
        var self = this;
        self.defaults = {
            parent : null
        };
        self.viewState = m.prop('form'); // 'processing', 'done', 'error';
        self.options = $.extend(self.defaults, options);
        self.init = function _init () {

        };
        self.add = function _add () {

        };
    },
    view : function (ctrl, options) {
        var templates = {
            form : m('.modal-content', [
                m('.modal-header', [
                    m('button.close[data-dismiss="modal"][aria-label="Close"]', [
                        m('span[aria-hidden="true"]','×'),
                    ]),
                    m('h3.modal-title#addProject', 'Add New Project')
                ]),
                m('.modal-body', [
                    m('p', 'You are adding project '),
                    m('.form-inline', [
                        m('.form-group', [
                            m('label[for="addCollInput]', 'Collection Name'),
                            m('input[type="text"].form-control.m-l-sm#addCollInput', {onchange: m.withAttr('value', ctrl.newCollectionName), value: ctrl.newCollectionName()})

                        ])
                    ]),
                    m('p.m-t-sm', 'After you create your collection drag and drop projects to the collection. ')
                ]),
                m('.modal-footer', [
                    m('button[type="button"].btn.btn-default[data-dismiss="modal"]', 'Cancel'),
                    m('button[type="button"].btn.btn-success', { onclick : ctrl.add },'Add')
                ])
            ]),
            processing : m('.modal-content', []),
            done : m('.modal-content', []),
            error : m('.modal-content', [])
        };

        return  m('.addProjectModal', [
            m('.modal.fade[tabindex=-1][role="dialog"][aria-labelledby="addProject"][aria-hidden="true"]',
                m('.modal-dialog',
                    templates[ctrl.viewState]
                )
            )
        ]);
    }
};