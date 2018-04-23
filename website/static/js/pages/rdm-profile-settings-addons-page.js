'use strict';

var $ = require('jquery');
var ko = require('knockout');
var bootbox = require('bootbox');

require('css/rdm-addon-settings.css');

var RdmAddonSettings = function() {
    var self = this;
    var buildHtml = function(data) {
        console.log(data);
        $('#addonSettings h4.addon-title').each(function() {
            var $h4 = $(this);
            var $parentDiv = $h4.parent('div');
            var addonName = $parentDiv.data('addon-short-name');
            console.log(addonName);
            var config = data[addonName];
            
            if (config['is_forced']) {
                $h4.find('small').remove();
            }
            if (config['has_external_accounts']) {
                if (!config['is_forced']) {
                    $h4.append('<br>');
                }
                var small = '<small>' + 
                    '<a class="pull-right text-primary import-account">' +
                    'Import Account from Admin</a></small>' +
                    '<div class="clearfix"></div>';
                $h4.append(small);
            }
            
            $h4.find('.import-account').on('click', function() {
                var context = ko.contextFor($parentDiv[0]);
                importAdminAccount(addonName, context);
            });
        });
    };
    
    var importAdminAccount = function(addonName, context) {
        var url = '/api/v1/rdm/addons/import/' + addonName + '/';
        $.ajax({
            url: url,
            type: 'GET'
        })
        .done(function(data) {
            context.$root.updateAccounts();
            if (context.$root.setMessage) {
                context.$root.setMessage('Successfully imported the account.', 'text-success');
            } else if (context.$root.changeMessage) {
                context.$root.changeMessage('Successfully imported the account.', 'text-success');
            }
        })
        .fail(function(xhr, status, error) {
            if (context.$root.setMessage) {
                context.$root.setMessage('Failed to import the account.', 'text-danger');
            } else if (context.$root.changeMessage) {
                context.$root.changeMessage('Failed to import the account.', 'text-danger');
            }
        });
    };
    
    self.init = function() {
        var url = '/api/v1/rdm/addons/';
        $.ajax({
            url: url,
            type: 'GET'
        })
        .done(function(data) {
            buildHtml(data);
        })
        .fail(function(xhr, status, error) {
            bootbox.alert({
                message: error,
                backdrop: true
            });
        });
    };
    
};
$(function() {
    (new RdmAddonSettings()).init();
});
