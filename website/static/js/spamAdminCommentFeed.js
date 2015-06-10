/**
 * Renders a log feed.
 **/
'use strict';

var ko = require('knockout');

var $osf = require('js/osfHelpers');


/**
* Log model.
*/
var SpamAdminComment = function(data) {
    var self = this;

    self.cid=data.cid;
    self.author = ko.observable(data.author.name);
    self.author_url = ko.observable(data.author.url);
    self.dateCreated = ko.observable(data.dateCreated);
    self.dateModified = ko.observable(data.dateModified);
    self.content = ko.observable(data.content);
    self.project = ko.observable(data.project);
    self.project_url=ko.observable(data.project_url);

};

SpamAdminComment.prototype.markSpam = function(){
    var self=this;
    var worked = $osf.postJSON(
            "/api/v1/spam_admin/mark_comment_as_spam/",
            {
                "cid":self.cid
            }
        )
    return worked;
}

SpamAdminComment.prototype.markHam = function(){
    var self=this;

    var worked = $osf.postJSON(
            "/api/v1/spam_admin/mark_comment_as_ham/",
            {
                "cid":self.cid
            }
        )
    return worked;
}

/**
* View model for a log list.
* @param {Log[]} logs An array of Log model objects to render.
*/
var SpamAdminCommentViewModel = function(spamAdminComments) {

    var self = this;
    self.spamAdminComments = ko.observableArray([]);
    self.total = ko.observable(0);
    self.fill_comment_list();
};

SpamAdminCommentViewModel.prototype.markHam = function(spamAdminComment){
    var self = this;

    var markHamRequest = spamAdminComment.markHam();
    markHamRequest.done(function(response) {

        //self.spamAdminComments.remove(spamAdminComment);
        $osf.growl('Comment Marked as Ham',"", 'success');
        self.fill_comment_list();
    });
    markHamRequest.fail(function(response) {
        console.log('inside markHam done but failed');
    });
};

SpamAdminCommentViewModel.prototype.markSpam = function(spamAdminComment){
    var self = this;

    var markHamRequest = spamAdminComment.markSpam();
    markHamRequest.done(function(response) {
        self.spamAdminComments.remove(spamAdminComment);
        $osf.growl('Comment Marked as Spam',"", 'success');
        self.fill_comment_list();
    });
    markHamRequest.fail(function(response) {
        console.log('inside markSpam done but failed');
    });
};

SpamAdminCommentViewModel.prototype.fill_comment_list = function(){
  var self = this;
  self.get_comments(90);
};

SpamAdminCommentViewModel.prototype.get_comments = function(amount) {
    var self=this;
    var request = self.fetch(amount);
    request.done(function(response) {
        var newComments = response.comments.map(function(data){
            return new SpamAdminComment(data);
        });
        //todo: figure out how to extend array all at once
        //it is better to extend an array at once rather then manually add multiple times because each addition
        //forces knockout to reload. apply is just pushing for each new comment.
        self.spamAdminComments.removeAll();
        self.spamAdminComments.push.apply(self.spamAdminComments, newComments);
        self.total(response.total);
    });
    request.fail(function(error){console.log(error);});
};

SpamAdminCommentViewModel.prototype.fetch = function(amount){
    var self=this;
    var query_url = "/api/v1/spam_admin/list_comments/";
    if (amount){
        query_url += amount;
    }
    var data = $.getJSON(query_url);
    return data;
};

////////////////
// Public API //
////////////////

function SpamAdminCommentFeed(selector, options) {
    var self = this;
    self.selector = selector;
    self.init();
};

//// Apply ViewModel bindings
SpamAdminCommentFeed.prototype.init = function() {
    var self = this;
    $osf.applyBindings(new SpamAdminCommentViewModel(self.spamAdminComments), self.selector);
};

module.exports = SpamAdminCommentFeed;