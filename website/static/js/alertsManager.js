'use strict';

var $ = require('jquery');
var ko = require('knockout');
var $osf = require('./osfHelpers');
var Raven = require('raven-js');

var AlertsViewModel = function() {
    var self = this;

    self.dismissedAlerts = ko.observableArray([]);
    self.location = ko.observable('');
    self.loading = ko.observable(false);
    self.isDismissed = function(id){
        if (!self.loading()){
            return self.dismissedAlerts().includes(id);
        }
        return true;
    };
    self.dismiss = function(id){
        var url = $osf.apiV2Url('/alerts/');
        var payload = {
            'data': {
                'type': 'alerts',
                'id': id,
                'attributes': {
                    'location': self.location()
                }
             }
         };
        var request = $osf.ajaxJSON(
            'POST',
            url,
            {'isCors': true, 'data': payload}
        );
        request.done(function (res) {

        });
        request.fail(function (xhr, status, error) {
            $osf.growl('Error', 'Could not dismiss alert. Please refresh page and try again.', 'danger');
            Raven.captureMessage('Error fetching user alerts', {
                extra: {
                    url: url,
                    status: status,
                    error: error
                }
            });
        });
    };

    self.fetchDismissedAlerts = function(){
        self.loading(true);
        var url = $osf.apiV2Url(
          '/alerts/', {
            query : {
                'filter[location]' : self.location(),
            }
          });
        var request = $osf.ajaxJSON(
          'GET',
          url,
          {'isCors': true}
        );
        request.done(function(res){
            var alerts = [];
            res.data.forEach(function(item){
                alerts.push(item.id);
            });
            self.dismissedAlerts(alerts);
            self.loading(false);
        });
        request.fail(function(xhr, status, error){
            self.loading(false);
            $osf.growl('Error', 'Could not fetch alerts for this page. Please refresh page and try again.', 'danger');
            Raven.captureMessage('Error fetching user alerts', {
                extra: {
                    url: url,
                    status: status,
                    error: error
                }
            });
        });
    };
};

////////////////
// Public API //
////////////////

function AlertManager(selector){
    var self = this;
    self.selector = selector;
    self.$element = $(selector);
    self.viewModel = new AlertsViewModel();
    self.init();
}

AlertManager.prototype.init = function() {
    ko.applyBindings(this.viewModel, this.$element[0]);
    this.viewModel.location(window.location.pathname);
    this.viewModel.fetchDismissedAlerts();
};

module.exports = AlertManager;
