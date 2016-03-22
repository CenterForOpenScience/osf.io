/**
 * Initialization code for the home page.
 */

'use strict';

var $ = require('jquery');
var m = require('mithril');

var QuickSearchProject = require('js/home-page/quickProjectSearchPlugin');
var NewAndNoteworthy = require('js/home-page/newAndNoteworthyPlugin');
var MeetingsAndConferences = require('js/home-page/meetingsAndConferencesPlugin');
var AddProject = require('js/addProjectPlugin');
var $osf = require('js/osfHelpers');
var Raven = require('raven-js');

var xhrconfig = function (xhr) {
    xhr.withCredentials = true;
    xhr.setRequestHeader('Content-Type', 'application/vnd.api+json;');
    xhr.setRequestHeader('Accept', 'application/vnd.api+json; ext=bulk');
};
var columnSizeClass = '.col-md-10 col-md-offset-1 col-lg-8 col-lg-offset-2';

$(document).ready(function(){
    var osfHome = {
        controller : function(){
            var self = this;
            self.categoryList = [];
            self.loadCategories = function _loadCategories () {
                var promise = m.request({method : 'OPTIONS', url : $osf.apiV2Url('nodes/', { query : {}}), config : xhrconfig});
                promise.then(function _success(results){
                    if(results.actions.POST.category){
                        self.categoryList = results.actions.POST.category.choices;
                        self.categoryList.sort(function(a, b){ // Quick alphabetical sorting
                            if(a.value < b.value) return -1;
                            if(a.value > b.value) return 1;
                            return 0;
                        });
                    }
                }, function _error(results){
                    var message = 'Error loading project category names for the home page.';
                    Raven.captureMessage(message, {requestReturn: results});
                });
                return promise;
            };
            self.loadCategories();

        },
        view : function(ctrl, args) {
            return [
                m('.quickSearch', m('.container.p-t-lg',
                    [
                        m('.row', [
                            m(columnSizeClass, m('h2.col-sm-9', 'My Dashboard'), m('.pull-right.col-sm-3',
                                m.component(AddProject, {
                                    buttonTemplate : m('button.btn.btn-success.btn-success-high-contrast.m-t-md.f-w-xl[data-toggle="modal"][data-target="#addProjectFromHome"]', {onclick: function(){
                                        $osf.trackClick('quickSearch', 'add-project', 'open-add-project-modal');
                                    }}, 'Create new project'),
                                    modalID : 'addProjectFromHome',
                                    categoryList : ctrl.categoryList,
                                    stayCallback : function _stayCallback_inPanel() {
                                        document.location.reload(true);
                                    },
                                    trackingCategory: 'quickSearch',
                                    trackingAction: 'add-project'
                                })
                            ))
                        ]),
                        m('.row.m-t-lg', [
                            m(columnSizeClass, m.component(QuickSearchProject, {}))
                        ])
                    ]
                )),
                m('.newAndNoteworthy', m('.container',
                    [
                        m('.row', [
                            m(columnSizeClass,m('h3', 'Discover Public Projects'))
                        ]),
                        m('.row', [
                            m(columnSizeClass, m.component(NewAndNoteworthy, {}))
                        ])

                    ]
                )),
                m('.meetings', m('.container',
                    [
                        m('.row', [
                            m(columnSizeClass,  m.component(MeetingsAndConferences, {}))
                        ])

                    ]
                ))
            ];
        }
    };
    // If logged in...
    m.mount(document.getElementById('osfHome'), m.component(osfHome, {}));



});
