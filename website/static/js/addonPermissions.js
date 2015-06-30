/**
 * Module for listing all projects/components authorized for a given addon
 * on the user settings page. Also handles revoking addon access from these
 * projects/components.
 */
'use strict';

var $ = require('jquery');
var bootbox = require('bootbox');

var $osf = require('js/osfHelpers');

var AddonPermissionsTable = {
    init: function(addonShortName, addonFullname) {
        $('.' + addonShortName + '-remove-token').on('click', function (event) {
            var nodeId = $(this).attr('node-id');
            var apiUrl = $(this).attr('api-url')+ addonShortName + '/config/';
            bootbox.confirm({
                title: 'Remove addon?',
                message: 'Are you sure you want to disconnnect the ' + addonFullname + ' account from this project?',
                callback: function (confirm) {
                    if (confirm) {
                        $.ajax({
                            type: 'DELETE',
                            url: apiUrl,

                            success: function (response) {

                                $('#' + addonShortName + '-' + nodeId + '-auth-row').hide();
                                var numNodes = $('#' + addonShortName + '-auth-table tr:visible').length;
                                if (numNodes === 1) {
                                    $('#' + addonShortName + '-auth-table').hide();
                                }
                                if (numNodes === 4) {
                                    $('#' + addonShortName + '-more').hide();
                                    $('#' + addonShortName+ '-less').hide();
                                }
                            },

                            error: function () {
                                $osf.growl('An error occurred, the account is still connected to the project. ',
                                    'If the issue persists, please report it to <a href="mailto:support@osf.io">support@osf.io</a>.');
                            }
                        });
                    }
                }
            });
    });

    $('#' + addonShortName + '-more').on('click', function (event) {
        $('#' + addonShortName + '-header').removeClass('table-less');
        $('#' + addonShortName + '-more').hide();
        $('#' + addonShortName + '-less').show();
    });
    $('#' + addonShortName + '-less').on('click', function (event) {
        $('#' + addonShortName + '-header').addClass('table-less');
        $('#' + addonShortName + '-less').hide();
        $('#' + addonShortName + '-more').show();
    });
    }
};

module.exports = AddonPermissionsTable;
