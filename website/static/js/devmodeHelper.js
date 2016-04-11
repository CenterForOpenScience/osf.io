var $ = require('jquery');
var ko = require('knockout');
var $osf = require('js/osfHelpers');

var DevModeModel = function() {
    self = this;
    self.pullRequests = ko.observableArray([]);
    self.showMetaInfo = ko.observable(false);
    self.showHideMetaInfo = function() {
        if(self.pullRequests().length === 0) {
            $.getJSON('/static/git_logs.json')
                .done(function(data){
                    dataLength = data.length;
                    for(i=0; i<dataLength; i++) {
                        self.pullRequests.push(new PullRequestItem(data[i]));
                    }
            });
        }
        self.showMetaInfo(!self.showMetaInfo());
    };
};

var PullRequestItem = function(prItem) {
    this.url = prItem.html_url || '';
    this.number = prItem.number || '';
    this.title = prItem.title || '';
    this.mergedAt = prItem.merged_at || '';

};

var DevModeControls = function(selector) {
    this.viewModel = new DevModeModel();
    $osf.applyBindings(this.viewModel, selector);
};

module.exports = DevModeControls;