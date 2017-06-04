'use strict';

var ko = require('knockout');
var Raven = require('raven-js');

var $osf = require('js/osfHelpers');


var ViewModel = function(context) {
    var self = this;
    self.ctx = context;
    self.allNodes = ko.observableArray();
    // Need to get the node
    self.fetchInstitutionNodes = function _fetchInstitutionNodes(){
        var url = self.ctx.apiV2Prefix + 'institutions/' + self.ctx.institution.id + '/?embed=nodes';
        return $osf.ajaxJSON(
            'GET',
            url,
            {
                isCors: true
            }
        ).done( function(response){
            self.allNodes(response.data.embeds.nodes.data);
        }).fail(function(xhr, status, error){
            Raven.captureMessage('Failed to load Institution\'s nodes', {
                extra: {
                    url: url,
                    textStatus: status,
                    err: error
                }
            });
        });
    };
};

var InstitutionNodes = function(selector, context)  {
    var viewModel = new ViewModel(context);
    viewModel.fetchInstitutionNodes();
    $osf.applyBindings(viewModel, selector);
};

module.exports = InstitutionNodes;
