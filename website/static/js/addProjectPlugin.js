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
            parentID : null,
            modalID : 'addProjectModal',
            stayCallback :null // Function to call when user decides to stay after project creation
        };
        self.viewState = m.prop('form'); // 'processing', 'success', 'error';
        self.options = $.extend(self.defaults, options);
        self.showMore = m.prop(false);
        self.newProjectName = m.prop('');
        self.newProjectDesc = m.prop('');
        self.newProjectCategory = m.prop('');
        self.goToProjectLink = m.prop('');
        self.saveResult = m.prop({});
        self.errorMessageType = m.prop('unknown');
        self.errorMessage = {
            'unknown' : 'There was an unknown error. Please try again later.'
        };
        // Load Category list from API
        self.categoryList = [];
        self.loadCategories = function () {
            var promise = m.request({method : 'OPTIONS', url : $osf.apiV2Url('nodes/', { query : {}}), config : xhrconfig}).then(function _success(results){
                if(results.actions.POST.category){
                    self.categoryList = results.actions.POST.category.choices;
                    self.categoryList.sort(function(a, b){ // Quick alphabetical sorting
                        if(a.value < b.value) return -1;
                        if(a.value > b.value) return 1;
                        return 0;
                    });
                    self.categoryList.forEach(function(cat){
                        if(cat.value === 'project'){
                            self.newProjectCategory(cat.value);
                        }
                    });
                }
            }, function _error(results){
                console.error('Error loading category names:', results);
            });
            return promise;
        };
        self.loadCategories();
        // Validation
        self.isValid = m.prop(false);
        self.checkValid = function () {
            var projectNameNotEmpty = self.newProjectName().trim().length > 0 ? true : false;
            if(projectNameNotEmpty){
                self.isValid(true);
            } else {
                self.isValid(false);
            }
        };
        self.add = function _add () {
            var url;
            var data;
            self.viewState('processing');
            if(self.options.parentID) {
                url = $osf.apiV2Url('nodes/' + self.options.parentID + '/children/', { query : {}});
            } else {
                url = $osf.apiV2Url('nodes/', { query : {}});
            }
            data = {
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
                self.saveResult(result);
            };
            var error = function _error (result) {
                self.viewState('error');
                console.log('error', result);
            };
            m.request({method : 'POST', url : url, data : data, config : xhrconfig})
                .then(success, error);
            self.newProjectName('');
        };
        self.reset = function _reset(){
            self.newProjectName('');
            self.viewState('form');
            self.newProjectDesc('');
            self.newProjectCategory(self.categoryList[0].value);
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
                    m('h3.modal-title', 'Add New Project')
                ]),
                m('.modal-body', [
                    m('.text-left', [
                        m('.form-group.m-v-sm', [
                            m('label[for="projectName].f-w-lg.text-bigger', 'Project Name'),
                            m('input[type="text"].form-control', {
                                onkeyup: function(ev){
                                    if (ev.which === 13) {
                                         ctrl.add();
                                    }
                                    ctrl.newProjectName($(this).val());
                                    ctrl.checkValid();
                                },
                                value : ctrl.newProjectName()
                            })
                        ]),
                        m('.text-muted', { onclick : function(){
                            ctrl.showMore(!ctrl.showMore());
                        }},[
                            ctrl.showMore() ? m('i.fa.fa-caret-down', { style: 'width: 10px;'}) : m('i.fa.fa-caret-right', { style: 'width: 10px;'}),
                            ' More (description, type)'
                        ]),
                        ctrl.showMore() ? [
                            m('.form-group.m-v-sm', [
                                m('label[for="projectDesc].f-w-lg.text-bigger', 'Project Description'),
                                m('textarea.form-control.noresize', {
                                    onchange: m.withAttr('value', ctrl.newProjectDesc),
                                    value : ctrl.newProjectDesc()
                                })
                            ]),
                            m('.f-w-lg.text-bigger','Category'),
                            m('.category-radio.p-h-md', [
                                ctrl.categoryList.map(function(cat){
                                    return m('.radio', m('label', [  m('input', {
                                        type: 'radio',
                                        name: 'projectCategory',
                                        value: cat.value,
                                        checked: ctrl.newProjectCategory() === cat.value,
                                        onchange : m.withAttr('value', ctrl.newProjectCategory)
                                    }), cat.display_name || m('i.text-muted', '(Empty category)') ]));

                                })
                            ])
                        ] : ''
                    ])
                ]),
                m('.modal-footer', [
                    m('button[type="button"].btn.btn-default[data-dismiss="modal"]', { onclick : ctrl.reset},  'Cancel'),
                    ctrl.isValid() ? m('button[type="button"].btn.btn-success', { onclick : ctrl.add },'Add') : m('button[type="button"].btn.btn-success[disabled]','Add')
                ])
            ]),
            processing : m('.modal-content',
                m('.modal-content',
                    m('.modal-header', [
                        m('button.close[data-dismiss="modal"][aria-label="Close"]',{ onclick : ctrl.reset}, [
                            m('span[aria-hidden="true"]','×'),
                        ]),
                    ]),
                    m('.modal-body.text-left', [
                            m('.add-project-processing', 'Saving your project...')
                        ]
                    )
                )
            ),
            success : m('.modal-content', [
                m('.modal-content',
                    m('.modal-body.text-left', [
                            m('button.close[data-dismiss="modal"][aria-label="Close"]',{ onclick : ctrl.reset}, [
                                m('span[aria-hidden="true"]','×'),
                            ]),
                            m('h4.p-md.add-project-success.text-success', 'Project created successfully!')
                        ]
                    ),
                    m('.modal-footer', [
                        m('button[type="button"].btn.btn-default[data-dismiss="modal"]', {
                            onclick : function() {
                                ctrl.reset();
                                ctrl.options.stayCallback.call(ctrl); // results are at ctrl.saveResult
                            }
                        },  'Keep Working Here'),
                        m('a.btn.btn-success', { href : ctrl.goToProjectLink() },'Go to New Project')
                    ])
                )
            ]),
            error : m('.modal-content', [
                m('.modal-content',
                    m('.modal-body.text-left', [
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

        return  m('span', [
            ctrl.options.buttonTemplate,
            m('#' + ctrl.options.modalID + '.modal.fade[tabindex=-1][role="dialog"][aria-labelledby="addProject"][aria-hidden="true"]',
                m('.modal-dialog',
                    templates[ctrl.viewState()]
                )
            )
        ]);
    }
};

module.exports = AddProject;