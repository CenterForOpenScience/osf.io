/**
 * Module for listing all projects/components authorized for a given addon
 * on the user settings page. Also handles revoking addon access from these
 * projects/components.
 */

var $ = require('jquery');
var $osf = require('osfHelpers');
var bootbox = require('bootbox');

var AddonPermissionsTable = {
    init: function(addonShortName, addonFullname) {
        $('.' + addonShortName + '-remove-token').on('click', function (event) {
        var nodeId = $(this).attr('node-id');
        bootbox.confirm({
            title: 'Remove addon?',
            message: 'Are you sure you want to remove the ' + addonFullname + ' authorization from this project?',
            callback: function (confirm) {
                if (confirm) {
                    $.ajax({
                        type: 'DELETE',
                        url: '/api/v1/project/' + nodeId + '/' + addonShortName + '/config/',

                        success: function (response) {

                            $("#" + addonShortName + "-" + nodeId + "-auth-row").hide();
                            var numNodes = $("#" + addonShortName + "-auth-table tr:visible").length;
                            if (numNodes === 1) {
                                $("#" + addonShortName + "-auth-table").hide();
                            }
                            if (numNodes === 4) {
                                $("#" + addonShortName + "-more").hide();
                                $("#" + addonShortName+ "-less").hide();
                            }
                        },

                        error: function () {
                            $osf.growl('An error occurred, the project has not been deauthorized. ',
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

// Needs to be in the global scope because AddonPermissionsTable
// is initialized in addon_permissions.mako
module.exports = window.AddonPermissionsTable = AddonPermissionsTable;
