'use strict';

var ko = require('knockout');
var $osf = require('js/osfHelpers');

var xhrconfig = function (xhr) {
    xhr.withCredentials = true;
    xhr.setRequestHeader('Content-Type', 'application/vnd.api+json;');
    xhr.setRequestHeader('Accept', 'application/vnd.api+json; ext=bulk');
};

var ViewModel = function(context) {
    var self = this;
    self.ctx = context;
    self.allNodes = ko.observable();
    self.instDescription = ko.observable();
    // Need to get the node
    self.fetchInstitutionNodes = function _fetchInstitutionNodes(){
        return $osf.ajaxJSON(
            'GET',
            self.ctx.apiV2Prefix + 'institutions/' + self.ctx.institution.id + '/?embed=nodes',
            {
                isCors: true,
            }
        ).done( function(response){
            self.allNodes(response.data.embeds.nodes.data);
            self.instDescription(response.data.attributes.description);
        }).fail(function(response){
        });
    };
};

var InstitutionNodes = function(selector, context)  {
    var viewModel = new ViewModel(context);
    viewModel.fetchInstitutionNodes();
    $osf.applyBindings(viewModel, selector);
};

module.exports = InstitutionNodes;
