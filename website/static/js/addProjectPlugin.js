/**
 * UI and function to add project
 */
'use strict';

require('css/add-project-plugin.css');
var $ = require('jquery');
var m = require('mithril');
var Cookie = require('js-cookie');
var $osf = require('js/osfHelpers');
var mHelpers = require('js/mithrilHelpers');
var institutionComponents = require('js/components/institution');
var SelectableInstitution = institutionComponents.SelectableInstitution;


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
        self.newProjectStorageLocation = m.prop(window.contextVars.storageRegions[0]); // first storage region is default
        self.storageRegions = m.prop(window.contextVars.storageRegions);
        self.newProjectCategory = m.prop(self.defaultCat);
        self.newProjectTemplate = m.prop('');
        self.newProjectInheritContribs = m.prop(false);
        self.newProjectInheritTags = m.prop(false);
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
            if (! self.isValid()) {
                return;
            }
            if (self.isAdding()) {
                return;
            }
            self.isAdding(true);
            var url;
            var data;
            self.viewState('processing');
            if(self.options.parentID) {
                url = $osf.apiV2Url('nodes/' + self.options.parentID + '/children/', { query : {'inherit_contributors' : self.newProjectInheritContribs(), 'version': '2.2', 'region': self.newProjectStorageLocation()._id}});
            } else {
                url = $osf.apiV2Url('nodes/', { query : {'version': '2.2', 'region': self.newProjectStorageLocation()._id}});
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

            if(self.newProjectInheritTags()){
                data.data.attributes.tags = window.contextVars.node.tags;
            }

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
            var request = m.request({method : 'POST', url : url, data : data, config : mHelpers.apiV2Config()});
            if (self.institutions.length > 0) {
                request.then(function (result) {
                    var newNodeApiUrl = $osf.apiV2Url('nodes/' + result.data.id + '/relationships/institutions/', {query: {'version': '2.2'}});
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
                        m.request({method: 'POST', url: newNodeApiUrl, data: data, config: mHelpers.apiV2Config()}).then(
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
                                    var val = ev.target.value;
                                    ctrl.isValid(val.trim().length > 0);
                                    if (ev.which === 13) {
                                        ctrl.add();
                                    }
                                    ctrl.newProjectName(val);
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
                        m('.form-group.m-v-sm', [
                            m('row',
                                m('f-w-lg.text-bigger', 'Storage location'),
                                m.component(SelectStorageLocation, {
                                    value: ctrl.newProjectStorageLocation,
                                    locations: ctrl.storageRegions
                                })
                            )
                            ]
                        ),
                        ctrl.options.parentID !== null && options.contributors.length && options.currentUserCanEdit ? m('.form-group.m-v-sm', [
                            m('label.f-w-md',

                                m('input', {
                                    type: 'checkbox',
                                    name: 'inherit_contributors',
                                    value: true,
                                    onchange : function() {
                                        ctrl.newProjectInheritContribs(this.checked);
                                    }
                                }), ' Add contributors from ', m('b', options.parentTitle),
                                m('br'),
                                m('i', ' Admins of ', m('b', options.parentTitle), ' will have read access to this component.')
                            ),
                            m('br'),
                            m('label.f-w-md',

                                m('input', {
                                    type: 'checkbox',
                                    name: 'inherit_tags',
                                    onchange : function() {
                                        ctrl.newProjectInheritTags(this.checked);
                                    }
                                }), ' Add tags from ', m('b', options.parentTitle)
                            )
                        ]) : '',
                        ctrl.options.parentID !== null ? m('.span', [
                                m('label.f-w-lg.text-bigger', 'License'),
                                m('p',
                                    m('i', ' This component will inherit the same license as ',
                                        m('b', options.parentTitle),
                                        '. ',
                                        m('a[href="http://help.osf.io/m/sharing/l/524050-licenses?id=524050-licenses"]', 'Learn more.' )
                                    )
                                )
                        ]): '',
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
                                m('i', ' (for descriptive purposes)'),
                                m('div.dropdown.dropup.generic-dropdown.category-list', [
                                    m('button[data-toggle="dropdown"]', {
                                        className: 'btn btn-default dropdown-toggle',
                                        type: 'button'
                                      }, [
                                        m('i', { className : mHelpers.getIcon(ctrl.newProjectCategory()) }),
                                        m('span.text-capitalize', ctrl.newProjectCategory() || 'Uncategorized'),
                                        m('i.fa.fa-sort')
                                      ]),
                                    m('ul.dropdown-menu', [
                                        mHelpers.unwrap(ctrl.options.categoryList).map(function(cat){
                                            return m('li',
                                                m('a', {
                                                        onclick : function(){
                                                              ctrl.newProjectCategory(cat.value);
                                                              $osf.trackClick(options.trackingCategory, options.trackingAction, 'select-project-category');
                                                            }
                                                  }, [
                                                    m('i', { className : mHelpers.getIcon(cat.value) }),
                                                    m('span', cat.display_name || '(Empty category)')
                                                  ]
                                                )
                                            );
                                        })
                                    ]),
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

var SelectStorageLocation = {
    view: function(ctrl, options) {
        return m('select.p-t-sm', {config: SelectStorageLocation.config(options)},
            [
            options.locations().map(function(region) {
                var args = {value: region._id};
                return m('option', args, region.name);
            })
        ]);
    },
    config: function(ctrl) {
        return function (element, isInitialized) {
            var $el = $(element);
            if (!isInitialized) {
                $el.select2({allowClear: true, width: '100%'}).on('change', function () {
                    var id = $el.select2('val');
                    m.startComputation();
                    //Set the value to the selected option
                    ctrl.locations().map(function (location) {
                        if (location._id === id) {
                            ctrl.value(location);
                        }
                    });
                    m.endComputation();
                });
            }
        };
    }
};

module.exports = AddProject;
