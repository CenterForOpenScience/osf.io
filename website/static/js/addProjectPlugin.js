/**
 * UI and function to add project
 */
'use strict';

require('css/add-project-plugin.css');
var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');

// XHR configuration to get apiserver connection to work
var xhrconfig = function (xhr) {
    xhr.withCredentials = true;
};


var AddProject = {
    controller : function (options) {
        var self = this;
        self.defaults = {
            buttonTemplate : m('.btn.btn-primary[data-toggle="modal"][data-target="#addProjectModal"]', 'Add new Project'),
            parent : null
        };
        self.viewState = m.prop('form'); // 'processing', 'success', 'error';
        self.options = $.extend(self.defaults, options);
        self.init = function _init () {

        };
        self.newProjectName = m.prop('');
        self.newProjectDesc = m.prop('');
        self.newProjectCategory = 'project';
        self.goToProjectLink = m.prop('');
        self.errorMessageType = m.prop('unknown');
        self.errorMessage = {
            'unknown' : 'There was an unknown error. Please try again later.'
        };
        self.chooseCategory = function(event){
            self.newProjectCategory = $(this).val();
        };
        self.add = function _add () {
            self.viewState('processing');
            var url = $osf.apiV2Url('nodes/', { query : {}});
            var data = {
                    'data' : {
                        'type': 'nodes',
                        'attributes': {
                            'title': self.newProjectName(),
                            'category': self.newProjectCategory,
                            'description' : self.newProjectDesc()
                        }
                    }
                };
            var success = function _success (result) {
                self.viewState('success');
                console.log('success', result);
                self.goToProjectLink(result.data.links.html);
            };
            var error = function _error (result) {
                self.viewState('error');
                console.log('error', result);
            };
            m.request({method : 'POST', url : url, data : data, config : xhrconfig})
                .then(success, error);
            self.newProjectName('');
            m.redraw(true);

        };
        self.reset = function _reset(){
            self.newProjectName('');
            self.viewState('form');
            $('.modal').modal('hide');
        };
    },
    view : function (ctrl, options) {
        var templates = {
            form : m('.modal-content', [
                m('.modal-header', [
                    m('button.close[data-dismiss="modal"][aria-label="Close"]',{ onclick : ctrl.reset}, [
                        m('span[aria-hidden="true"]','×'),
                    ]),
                    m('h3.modal-title#addProject', 'Add New Project')
                ]),
                m('.modal-body', [
                    m('', [
                        m('.form-group.m-v-sm', [
                            m('label[for="projectName].f-w-lg.text-bigger', 'Project Name'),
                            m('input[type="text"].form-control#projectName', {
                                onkeyup: function(ev){
                                    if (ev.which === 13) {
                                         ctrl.add();
                                    }
                                    ctrl.newProjectName($(this).val());
                                },
                                value : ctrl.newProjectName()
                            })
                        ]),
                        m('.form-group.m-v-sm', [
                            m('label[for="projectDesc].f-w-lg.text-bigger', 'Project Description'),
                            m('textarea.form-control#projectDesc', {
                                onkeyup: function(ev){
                                    ctrl.newProjectDesc($(this).val());
                                },
                                value : ctrl.newProjectDesc()
                            })
                        ]),
                        m('.f-w-lg.text-bigger','Category'),
                        m('.category-radio.p-h-md', [
                            m('.radio', m('label', [m('input[type="radio"][name="projectCategory][id="catProject][value="project][checked="checked"]',{ onchange : ctrl.chooseCategory }), 'Project'])),
                            m('.radio', m('label', [m('input[type="radio"][name="projectCategory][id="catHypothesis][value="hypothesis"]',{ onchange : ctrl.chooseCategory }), 'Hypothesis'])),
                            m('.radio', m('label', [m('input[type="radio"][name="projectCategory][id="catmethods][value="methods and measures"]',{ onchange : ctrl.chooseCategory }), 'Methods and Measures'])),
                            m('.radio', m('label', [m('input[type="radio"][name="projectCategory][id="catprocedure][value="procedure"]',{ onchange : ctrl.chooseCategory }), 'Procedure'])),
                            m('.radio', m('label', [m('input[type="radio"][name="projectCategory][id="catinstrumentation][value="instrumentation"]',{ onchange : ctrl.chooseCategory }), 'Instrumentation'])),
                            m('.radio', m('label', [m('input[type="radio"][name="projectCategory][id="catdata][value="data"]',{ onchange : ctrl.chooseCategory }), 'Data'])),
                            m('.radio', m('label', [m('input[type="radio"][name="projectCategory][id="catanalysis][value="analysis"]',{ onchange : ctrl.chooseCategory }), 'Analysis'])),
                            m('.radio', m('label', [m('input[type="radio"][name="projectCategory][id="catcommunication][value="communication"]',{ onchange : ctrl.chooseCategory }), 'Communication'])),
                            m('.radio', m('label', [m('input[type="radio"][name="projectCategory][id="catother][value="other"]',{ onchange : ctrl.chooseCategory }), 'Other']))
                        ])
                    ])
                ]),
                m('.modal-footer', [
                    m('button[type="button"].btn.btn-default[data-dismiss="modal"]', { onclick : ctrl.reset},  'Cancel'),
                    m('button[type="button"].btn.btn-success', { onclick : ctrl.add },'Add')
                ])
            ]),
            processing : m('.modal-content',
                m('.modal-content',
                    m('.modal-header', [
                        m('button.close[data-dismiss="modal"][aria-label="Close"]',{ onclick : ctrl.reset}, [
                            m('span[aria-hidden="true"]','×'),
                        ]),
                    ]),
                    m('.modal-body', [
                            m('.add-project-processing', 'Saving your project...')
                        ]
                    )
                )
            ),
            success : m('.modal-content', [
                m('.modal-content',
                    m('.modal-body', [
                            m('button.close[data-dismiss="modal"][aria-label="Close"]',{ onclick : ctrl.reset}, [
                                m('span[aria-hidden="true"]','×'),
                            ]),
                            m('h4.p-md.add-project-success.text-success', 'Project created successfully!')
                        ]
                    ),
                    m('.modal-footer', [
                        m('button[type="button"].btn.btn-default[data-dismiss="modal"]', { onclick : ctrl.reset },  'Keep Working Here'),
                        m('a.btn.btn-success', { href : ctrl.goToProjectLink() },'Go to New Project')
                    ])
                )
            ]),
            error : m('.modal-content', [
                m('.modal-content',
                    m('.modal-body', [
                            m('button.close[data-dismiss="modal"][aria-label="Close"]',{ onclick : ctrl.reset}, [
                                m('span[aria-hidden="true"]','×'),
                            ]),
                            m('h4.p-md.add-project-error.text-danger', 'Couldn\'t create your project'),
                            m('p', ctrl.errorMessage[ctrl.errorMessageType()])
                        ]
                    )
                )
            ])
        };

        return  m('', [
            ctrl.options.buttonTemplate,
            m('#addProjectModal.modal.fade[tabindex=-1][role="dialog"][aria-labelledby="addProject"][aria-hidden="true"]',
                m('.modal-dialog',
                    templates[ctrl.viewState()]
                )
            )
        ]);
    }
};

module.exports = AddProject;