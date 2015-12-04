'use strict';

var $osf = require('js/osfHelpers');
var ko = require('knockout');
var $ = require('jquery');

var drafts;

ko.bindingHandlers.enterkey = {
    init: function (element, valueAccessor, allBindings, viewModel) {
        var callback = valueAccessor();
        $(element).keypress(function (event) {
            var keyCode = (event.which ? event.which : event.keyCode);
            if (keyCode === 13) {
                callback.call(viewModel);
                return false;
            }
            return true;
        });
    }
};

/**
* Assignee column.
*
* @param  {List} reviewers  The prereg reviewers who can be assigned
*/
var Assignee = function(reviewers) {
    var self = this;
    self.edit = ko.observable(false);

    if (reviewers[0] !== 'none') {
        reviewers.unshift('none'); 
    }
    
    self.reviewers = ko.observableArray(reviewers);
    self.assignee = ko.observable('none');
};

Assignee.prototype.editItem = function() {
    var self = this;
    self.assignee.edit(!self.editing);
    self.editing(!self.editing);
    
};

/**
* Proof of publication column.
*/
var ProofOfPub = function() {
    var self = this;
    self.edit = ko.observable(false);
    self.proofOfPub = ko.observable('Published Article Not Yet Submitted');
    self.proofOfPubList = ko.observableArray(['Published Article Not Yet Submitted', 'Published Article Submitted', 'Published Article Under Review', 'Published Article Approved', 'Published Article Rejected']);
};

ProofOfPub.prototype.editItem = function() {
    var self = this;
    self.proofOfPub.edit(!self.editing);
    self.editing(!self.editing);
};

/**
* Payment sent column.
*/
var PaymentSent = function() {
    var self = this;
    self.edit = ko.observable(false);
    self.paymentSent = ko.observable('no');
    self.paymentSentList = ko.observableArray(['Yes', 'No']);
};

PaymentSent.prototype.editItem = function() {
    var self = this;
    self.paymentSent.edit(!self.editing);
    self.editing(!self.editing);
};

/**
* Notes column.
*/
var Notes = function() {
    var self = this;
    self.edit = ko.observable(false);
    self.notes = ko.observable('none');
};

Notes.prototype.enlargeIcon = function(data, event) {
    var icon = event.currentTarget;
    $(icon).addClass("fa-2x");
};

Notes.prototype.shrinkIcon = function(data, event) {
    var icon = event.currentTarget;
    $(icon).removeClass("fa-2x");
};
Notes.prototype.editItem = function() {
    var self = this;
    self.editing(true);
    self.notes.edit(true);
};

Notes.prototype.stopEditing = function() {
    var self = this;
    self.editing(false);
    self.notes.edit(false);
};

/**
* The row containing the information for a single draft displayed in columns.
*
* @param  {Dict}    params     The draft information
* @param  {String}  permission Whether the admin can assign a reviewer
* @param  {List}    reviewers  The prereg reviewers who can be assigned
*/
var Row = function(params, permission, reviewers) {
    var self = this;

    self.params = params;
    self.viewingDraft = ko.observable(false);
    if (permission === "false") {
        permission = false;
    } else {
        permission = true;
    }
    self.adminPermission = ko.observable(permission);

    self.editing = ko.observable(false);

    self.title = params.registration_metadata.q1.value || 'no title';
    self.fullname = params.initiator.fullname;
    self.username = params.initiator.emails[0].address;
    self.initiated = self.formatTime(params.initiated);
    self.updated = self.formatTime(params.updated);
    self.status = ko.observable(params.is_pending_approval ? 'pending approval': 'approved');

    self.proofOfPub = new ProofOfPub();
    self.paymentSent = new PaymentSent();
    self.notes = new Notes();
    self.assignee = new Assignee(reviewers); 
};


Row.prototype.highlightRow = function(data, event) {  
    var row = event.currentTarget;
    $(row).css("background","#E0EBF3"); 
};

Row.prototype.unhighlightRow = function(data, event) {
    var row = event.currentTarget;
    $(row).css("background",""); 
};

Row.prototype.formatTime = function(time) {
    var parsedTime = time.split(".");
    return parsedTime[0]; 
};

Row.prototype.goToDraft = function(data, event) {
    var self = this;
    if (self.editing() === false) {
        self.viewingDraft(true);
        document.location.href = 'drafts/' + self.params.pk + '/';
    }
};

/**
* The view containing all of the rows with draft information.
*
* @param  {String}  adminSelector   The class to bind to
* @param  {String}  user            The current user
* @param  {List}    reviewers       The prereg reviewers who can be assigned
*/
var AdminView = function(adminSelector, user, reviewers) {
    var self = this;

    self.adminSelector = adminSelector;
    self.user = user;
    self.reviewers = reviewers;

    self.getDrafts = $.getJSON.bind(null, "drafts/");

    self.drafts = ko.observable([]);
    self.loading = ko.observable(true);

    self.sortBy = ko.observable('title');
    self.sortedDrafts = ko.computed(function() {
        var row = self.sortBy();
        return self.drafts().sort(function (left, right) { 
            var a = deep_value(left, row).toLowerCase();
            var b = deep_value(right, row).toLowerCase();
            return a == b ? 0 : 
                (a < b ? -1 : 1); 
        });
    });
};

AdminView.prototype.init = function() {
    var self = this;

    var getDrafts = self.getDrafts();

    // create new view model for each row
    getDrafts.then(function(response) {
        self.drafts(
            $.map(response.drafts, function(draft){
                return new Row(draft, self.user.admin, self.reviewers);
            })
        );
    });

    $.when(getDrafts).then(function() {
        self.loading(false);
    });
};

AdminView.prototype.setSort = function(data, event) {
    var self = this;
    self.sortBy(event.target.id);
};

/**
* Load values from prereg-admin-page.html.
*/
$(document).ready(function() {
    var user = prereg_user;
    var reviewers = prereg_reviewers;
    var adminView = new AdminView('#prereg-row', user, reviewers);
    adminView.init();
    ko.applyBindings(adminView, $('#prereg-row')[0]);
});

/**
* Gets value from nested properties.
*
* @param  {Dict}    obj    The object to find value from
* @param  {String}  path   Path to nested property
* @return {String}  
*/
var deep_value = function(obj, path){
    for (var i=0, path=path.split('.'), len=path.length; i<len; i++){
        if (obj === undefined) {
            return "No title";
        }
        if (path[i].indexOf('(') === -1) {
            obj = obj[path[i]];
        } else {
            var func = path[i].split('(');
            obj = obj[func[0]]();
        }
        
    };
    return obj;
};
