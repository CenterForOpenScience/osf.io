/**
 * Renders a project feed.
 **/
'use strict';

var ko = require('knockout');

var $osf = require('js/osfHelpers');


/**
* project model.
*/
var SpamAdminProject = function(data) {
    var self = this;

    self.pid=data.pid;
    self.author = ko.observable(data.author.name);
    self.emails = ko.observableArray(data.author.emails);
    self.dateCreated = ko.observable(data.date_created);
    self.dateModified = ko.observable(data.date_modified);
    self.description = ko.observable(data.description);
    self.title = ko.observable(data.title);
    self.url=ko.observable(data.url);
    self.wikis=ko.observableArray(data.wikis);
    self.tags=ko.observableArray(data.tags);
    self.components=ko.observableArray(data.components);


};


SpamAdminProject.prototype.markSpam = function(){
    var self=this;
    var worked = $osf.postJSON(
            "/api/v1/spam_admin/mark_project_as_spam/",
            {
                "pid":self.pid
            }
        )
    return worked;
}


SpamAdminProject.prototype.markHam = function(){
    var self=this;

    var worked = $osf.postJSON(
            "/api/v1/spam_admin/mark_project_as_ham/",
            {
                "pid":self.pid
            }
        )

    return worked;
}


/**
* View model for a project list.
* @param {project[]} projects An array of project model objects to render.
*/
var SpamAdminProjectViewModel = function(spamAdminProjects) {

    var self = this;
    self.spamAdminProjects = ko.observableArray([]);

    self.total = ko.observable(0);

    self.fill_project_list();



};


SpamAdminProjectViewModel.prototype.markHam = function(spamAdminProject){
    var self = this;


    var markHamRequest = spamAdminProject.markHam();
    markHamRequest.done(function(response) {

        self.spamAdminProjects.remove(spamAdminProject);
        $osf.growl('Project Marked as Ham',"", 'success');
        self.fill_project_list();

    });
    markHamRequest.fail(function(response) {
        console.log('inside markHam done but failed');
    });



};

SpamAdminProjectViewModel.prototype.markSpam = function(spamAdminProject){
    var self = this;

    var markHamRequest = spamAdminProject.markSpam();
    markHamRequest.done(function(response) {

        self.spamAdminProjects.remove(spamAdminProject);
        $osf.growl('Project Marked as Spam',"", 'success');
        self.fill_project_list();
    });
    markHamRequest.fail(function(response) {
        console.log('inside markSpam done but failed');
    });


};




SpamAdminProjectViewModel.prototype.fill_project_list = function(){
  var self = this;
  self.get_projects(30);
};

SpamAdminProjectViewModel.prototype.get_projects = function(amount) {


    var self=this;

    var request = self.fetch(amount);
    request.done(function(response) {
        console.log(response);
        var newProjects = response.projects.map(function(data){

            return new SpamAdminProject(data);
        });


        self.spamAdminProjects.removeAll();
        //it is better to extend an array at once rather then manually add multiple times because each addition
        //forces knockout to reload. DO THAT. apply is just pushing foreach new project. SLOW. FIX. TODO: make fast.
        self.spamAdminProjects.push.apply(self.spamAdminProjects, newProjects);


        self.total(response.total);

    });
    request.fail(function(error){console.log(error);});

};


SpamAdminProjectViewModel.prototype.fetch = function(amount){
    var self=this;

    var query_url = "/api/v1/spam_admin/list_projects/";
    if (amount){
        query_url += amount;
    }


    var data = $.getJSON(query_url);
    return data;
};








////////////////
// Public API //
////////////////



function SpamAdminProjectFeed(selector, options) {

    var self = this;
    self.selector = selector;

    self.init();



};







//// Apply ViewModel bindings
SpamAdminProjectFeed.prototype.init = function() {

    var self = this;


    $osf.applyBindings(new SpamAdminProjectViewModel(self.spamAdminProjects), self.selector);



};

module.exports = SpamAdminProjectFeed;