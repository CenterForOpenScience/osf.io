/**
 * UI and function to add project
 */
'use strict';

require('css/add-project-plugin.css');
var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');
var institutionComponents = require('js/components/institution');
var SelectableInstitution = institutionComponents.SelectableInstitution;

// XHR configuration to get apiserver connection to work
var xhrconfig = function (xhr) {
    xhr.withCredentials = true;
};


var AddProject = {
    controller : function (options) {
        var self = this;
        self.defaults = {
            buttonTemplate : m('.btn.btn-primary[data-toggle="modal"][data-target="#addProjectModal"]', 'Create new project'),
            parentID : null,
            parentTitle : '',
            title : 'Create new project',
            modalID : 'addProjectModal',
            stayCallback :null, // Function to call when user decides to stay after project creation
            categoryList : [],
            contributors : [],
            currentUserCanEdit : false
        };
        self.viewState = m.prop('form'); // 'processing', 'success', 'error';
        self.options = $.extend({}, self.defaults, options);
        self.nodeType = self.options.parentID === null ? 'project' : 'component';
        self.defaultCat = self.options.parentID === null ? 'project' : '';
        self.showMore = m.prop(false);
        self.newProjectName = m.prop('');
        self.newProjectDesc = m.prop('');
        self.newProjectCategory = m.prop(self.defaultCat);
        self.newProjectTemplate = m.prop('');
        self.newProjectInheritContribs = m.prop(false);
        self.institutions = options.institutions || window.contextVars.currentUser.institutions || [];
        self.checkedInstitutions = {};
        self.institutions.map(
            function(inst){
                self.checkedInstitutions[inst.id] = true;
                return inst.id;
            }
        );
        self.goToProjectLink = m.prop('');
        self.saveResult = m.prop({});
        self.errorMessageType = m.prop('unknown');
        self.errorMessage = {
            'unknown' : 'There was an unknown error. Please try again later.'
        };
        self.userProjects =  m.prop([]); // User nodes

        // Validation
        self.isValid = m.prop(false);

        self.isAdding = m.prop(false);

        self.mapTemplates = function() {
            self.userProjects([]);
            options.templatesFetcher._flat.map(function(node){
                self.userProjects().push({title: node.attributes.title, id: node.id});
            });
            return self.userProjects();
        };

        if(options.templatesFetcher){
            options.templatesFetcher.on(['page', 'done'], self.mapTemplates);
            if(self.userProjects().length === 0){ // Run this in case fetcher callbacks have already finished
                self.mapTemplates();
            }
        }


        self.add = function _add () {
            if (self.isAdding()) {
                return;
            }
            self.isAdding(true);
            var url;
            var data;
            self.viewState('processing');
            if(self.options.parentID) {
                url = $osf.apiV2Url('nodes/' + self.options.parentID + '/children/', { query : {'inherit_contributors' : self.newProjectInheritContribs()}});
            } else {
                url = $osf.apiV2Url('nodes/', { query : {}});
            }
            data = {
                    'data' : {
                        'type': 'nodes',
                        'attributes': {
                            'title': self.newProjectName(),
                            'category': self.newProjectCategory(),
                            'description': self.newProjectDesc()
                        }
                    }
                };

            if (self.newProjectTemplate()) {
                data.data.attributes.template_from = self.newProjectTemplate();
            }

            var success = function _success (result) {
                self.viewState('success');
                self.goToProjectLink(result.data.links.html);
                self.saveResult(result);
                self.isAdding(false);
            };
            var error = function _error (result) {
                self.viewState('error');
                self.isAdding(false);
            };
            var request = m.request({method : 'POST', url : url, data : data, config : xhrconfig});
            if (self.institutions.length > 0) {
                request.then(function (result) {
                    var newNodeApiUrl = $osf.apiV2Url('nodes/' + result.data.id + '/relationships/institutions/');
                    var data = {
                        data: self.institutions.filter(
                            function (inst) {
                                return self.checkedInstitutions[inst.id];
                            }
                        ).map(
                            function (inst) {
                                return {type: 'institutions', id: inst.id};
                            }
                        )
                    };
                    if (data.data.length > 0){
                        m.request({method: 'POST', url: newNodeApiUrl, data: data, config: xhrconfig}).then(
                            function(){},
                            function(){
                                self.viewState('instError');
                            }
                        );
                    }
                });
            }
            request.then(success, error);
            self.newProjectName('');
            self.newProjectDesc('');
            self.isValid(false);
        };
        self.reset = function _reset(){
            self.newProjectName('');
            $('#' + self.options.modalID + ' .project-name').val('');
            $('#' + self.options.modalID + ' .project-desc').val('');
            self.viewState('form');
            self.newProjectDesc('');
            self.newProjectCategory(self.defaultCat);
            self.newProjectInheritContribs(false);
            $('.modal').modal('hide');
            self.isValid(false);
        };
    },
    view : function (ctrl, options) {
        var templates = {
            form : m('.modal-content', [
                m('.modal-header', [
                    m('button.close[data-dismiss="modal"][aria-label="Close"]',{ onclick : function() {
                        ctrl.reset();
                        $osf.trackClick(options.trackingCategory, options.trackingAction, 'click-close-add-project-modal');
                    }}, [
                        m('span[aria-hidden="true"]','×')
                    ]),
                    m('h3.modal-title', ctrl.options.title)
                ]),
                m('.modal-body', [
                    m('.text-left', [
                        m('.form-group.m-v-sm', [
                            m('label[for="projectName].f-w-lg.text-bigger', 'Title'),
                            m('input[type="text"].form-control.project-name', {
                                onkeyup: function(ev){
                                    if (ev.which === 13) {
                                         ctrl.add();
                                    }
                                    var val = ev.target.value;
                                    ctrl.newProjectName(val);
                                    ctrl.isValid(val.trim().length > 0);
                                },
                                onchange: function(ev) {
                                    //  This will not be reliably running!
                                    $osf.trackClick(options.trackingCategory, options.trackingAction, 'type-project-name');
                                },
                                placeholder : 'Enter ' + ctrl.nodeType + ' title',
                                name : 'projectName'
                            })
                        ]),
                        ctrl.institutions.length ? m('.form-group.m-v-sm', [
                            m('label.f-w-lg.text-bigger', 'Affiliation'),
                            m('a', {onclick: function(){
                                ctrl.institutions.map(
                                    function(inst){
                                        ctrl.checkedInstitutions[inst.id] = false;
                                    }
                                );
                            }, style: {float: 'right'}},'Remove all'),
                            m('a', {onclick: function(){
                                ctrl.institutions.map(
                                    function(inst){
                                        ctrl.checkedInstitutions[inst.id] = true;
                                    }
                                );
                            }, style: {float: 'right', marginRight: '12px'}}, 'Select all'),
                            m('table', m('tr', ctrl.institutions.map(
                                function(inst){
                                    return m('td',
                                        m('a', {onclick: function(){
                                            ctrl.checkedInstitutions[inst.id] = !ctrl.checkedInstitutions[inst.id];

                                        }},m('', {style: {position: 'relative',  margin: '10px'}, width: '45px', height: '45px'},
                                            m.component(SelectableInstitution, {name: inst.name, width: '45px', logoPath: inst.logo_path, checked: ctrl.checkedInstitutions[inst.id]})
                                        ))
                                    );
                                }
                            ))),
                        ]): '',
                        ctrl.options.parentID !== null && options.contributors.length && options.currentUserCanEdit ? m('.form-group.m-v-sm', [
                            m('label.f-w-md',

                                m('input', {
                                    type: 'checkbox',
                                    name: 'inherit_contributors',
                                    value: true,
                                    onchange : function() {
                                        ctrl.newProjectInheritContribs(this.checked);
                                    }
                                }), ' Add contributors from ', m('b', options.parentTitle)
                            )
                        ]) : '',
                        m('.text-muted.pointer', { onclick : function(){
                            ctrl.showMore(!ctrl.showMore());
                            $osf.trackClick(options.trackingCategory, options.trackingAction, 'show-more-or-less');
                        }},[
                            ctrl.showMore() ? m('i.fa.fa-caret-down', { style: 'width: 10px;'}) : m('i.fa.fa-caret-right', { style: 'width: 10px;'}),
                            ' More'
                        ]),
                        ctrl.showMore() ? [
                            m('.form-group.m-v-sm', [
                                m('label[for="projectDesc].f-w-lg.text-bigger', 'Description'),
                                m('input[type="text"].form-control.noresize.project-desc', {
                                    onkeyup: function (ev){
                                        ctrl.newProjectDesc($(this).val());
                                    },
                                    onchange: function() {
                                        $osf.trackClick(options.trackingCategory, options.trackingAction, 'type-project-description');
                                    },
                                    name : 'projectDesc',
                                    placeholder : 'Enter ' + ctrl.nodeType + ' description'
                                })
                            ]),
                            ctrl.options.parentID !== null ? [
                                m('label.f-w-lg.text-bigger','Category'),
                                m('select.form-control', {
                                    onchange : function(event) {
                                        ctrl.newProjectCategory(this.value);
                                        $osf.trackClick(options.trackingCategory, options.trackingAction, 'select-project-category');
                                    }},
                                    [
                                        ctrl.options.categoryList.map(function(cat){
                                            return m('option', {
                                                type: 'option',
                                                name: 'projectCategory',
                                                value: cat.value,
                                                selected: ctrl.newProjectCategory() === cat.value
                                            }, cat.display_name|| m('i.text-muted', '(Empty category)'));

                                        })
                                    ])
                            ] : '',
                             ctrl.options.parentID === null ? m('.form-group.m-v-md', [
                                m('label[for="projectTemplate].f-w-lg.text-bigger', 'Template (optional)'),
                                m('p.f-w-xs.help-text', 'Start typing to search your projects. Selecting project as template will duplicate its ' +
                                    'structure in the new project without importing the content of that project.'),
                                m.component(Select2Template, {
                                    value: ctrl.newProjectTemplate,
                                    trackingCategory: options.trackingCategory,
                                    trackingAction: options.trackingAction,
                                    userProjects: ctrl.userProjects
                                })
                            ]) : ''
                        ] : ''
                    ])
                ]),
                m('.modal-footer', [
                    m('button[type="button"].btn.btn-default[data-dismiss="modal"]', { onclick : function(){
                        ctrl.reset();
                        $osf.trackClick(options.trackingCategory, options.trackingAction, 'click-cancel-button');
                    }},  'Cancel'),
                    ctrl.isValid() ? m('button[type="button"].btn.btn-success', { onclick : function(){
                        ctrl.add();
                        $osf.trackClick(options.trackingCategory, options.trackingAction, 'click-create-button');
                    }},'Create') : m('button[type="button"].btn.btn-success[disabled]','Create')
                ])
            ]),
            processing : m('.modal-content',
                m('.modal-content',
                    m('.modal-header', [
                        m('button.close[data-dismiss="modal"][aria-label="Close"]',{ onclick : ctrl.reset}, [
                            m('span[aria-hidden="true"]','×')
                        ])
                    ]),
                    m('.modal-body.text-left', [
                            m('.add-project-processing', 'Saving your ' + ctrl.nodeType + '...')
                        ]
                    )
                )
            ),
            success : m('.modal-content', [
                m('.modal-content',
                    m('.modal-body.text-left', [
                            m('button.close[data-dismiss="modal"][aria-label="Close"]',{ onclick : function() {
                                ctrl.reset();
                                $osf.trackClick(options.trackingCategory, options.trackingAction, 'click-close-success-modal');
                            }}, [
                                m('span[aria-hidden="true"]','×')
                            ]),
                            m('h4.add-project-success.text-success', 'New ' + ctrl.nodeType + ' created successfully!')
                        ]
                    ),
                    m('.modal-footer', [
                        m('button[type="button"].btn.btn-default[data-dismiss="modal"]', {
                            onclick : function() {
                                ctrl.reset();
                                ctrl.options.stayCallback.call(ctrl); // results are at ctrl.saveResult
                                $osf.trackClick(options.trackingCategory, options.trackingAction, 'keep-working-here');
                            }
                        },  'Keep working here'),
                        m('a.btn.btn-success', {
                            href : ctrl.goToProjectLink(),
                            onclick: function(){
                            $osf.trackClick(options.trackingCategory, options.trackingAction, 'go-to-new-project');
                            }
                        },'Go to new ' + ctrl.nodeType + '')
                    ])
                )
            ]),
            error : m('.modal-content', [
                m('.modal-content',
                    m('.modal-body.text-left', [
                            m('button.close[data-dismiss="modal"][aria-label="Close"]',{ onclick : function() {
                                ctrl.reset();
                                $osf.trackClick(options.trackingCategory, options.trackingAction, 'close-couldn\'t-create-your-project');
                                }}, [
                                m('span[aria-hidden="true"]','×')
                            ]),
                            m('h4.add-project-error.text-danger', 'Couldn\'t create your ' + ctrl.nodeType + ''),
                            m('p', ctrl.errorMessage[ctrl.errorMessageType()])
                        ]
                    ),
                    m('.modal-footer', [
                        m('button[type="button"].btn.btn-default[data-dismiss="modal"]', {onclick: function() {
                            $osf.trackClick(options.trackingCategory, options.trackingAction, 'click-OK-couldn\'t-create-your-project');
                        }},  'OK')
                    ])
                )
            ]),
            instError: m('.modal-content', [
                m('.modal-content',
                    m('.modal-body.text-left', [
                            m('button.close[data-dismiss="modal"][aria-label="Close"]',{ onclick : function() {
                                ctrl.reset();
                                }}, [
                                m('span[aria-hidden="true"]','×')
                            ]),
                            m('h4.add-project-error.text-danger', 'Could not add institution affiliation to your new ' + ctrl.nodeType + ''),
                            m('p', ctrl.errorMessage[ctrl.errorMessageType()])
                        ]
                    ),
                    m('.modal-footer', [
                        m('button[type="button"].btn.btn-default[data-dismiss="modal"]', {
                            onclick : function() {
                                ctrl.reset();
                                ctrl.options.stayCallback.call(ctrl); // results are at ctrl.saveResult
                            }
                        },  'Keep working here'),
                        m('a.btn.btn-success', {
                            href : ctrl.goToProjectLink()
                        },'Go to new ' + ctrl.nodeType + '')
                    ])
                )
            ])
        };

        return  m('span', [
            ctrl.options.buttonTemplate,
            m('#' + ctrl.options.modalID + '.modal.fade[tabindex=-1][role="dialog"][aria-labelledby="addProject"][aria-hidden="true"]',
                m('.modal-dialog.text-left',
                    templates[ctrl.viewState()]
                )
            )
        ]);
    }
};

var Select2Template = {
    view: function(ctrl, options) {
        return m('select', {config: Select2Template.config(options), onchange: function(){
            $osf.trackClick(options.trackingCategory, options.trackingAction, 'select-project-template');
        }}, [
            m('option', {value: ''}, ''),
            options.userProjects().map(function(node) {
                var args = {value: node.id};
                return m('option', args, node.title);
            })
        ]);
    },
    /**Select2 config factory - adapted from https://lhorie.github.io/mithril/integration.html **/
    config: function(ctrl) {
        return function(element, isInitialized) {
            var $el = $(element);
            if (!isInitialized) {
                $el.select2({placeholder: 'Select a project to use as a template', allowClear: true, width: '100%'}).on('change', function(e) {
                    var id = $el.select2('val');
                    m.startComputation();
                    //Set the value to the selected option
                    ctrl.userProjects().map(function(node){
                        if(node.id === id) {
                            ctrl.value(node.id);
                        }
                    });
                    m.endComputation();
                });
            }
        };
    }
};

module.exports = AddProject;
