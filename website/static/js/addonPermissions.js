/**
 * View model that controls the Dropbox configuration on the user settings page.
 */
;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['knockout', 'jquery', 'osfutils', 'language'], factory);
    } else if (typeof $script === 'function') {
        global.AddonUserConfig  = factory(ko, jQuery);
        $script.done('addonUserConfig');
    } else {
        global.AddonUserConfig  = factory(ko, jQuery);
    }
}(this, function(ko, $) {
        'use strict';

    function PermissionsViewModel(addonFullTitle, nodes) {
        self.nodes = ko.observableArray();
        self.addonFullTitle = ko.observableArray();

        self.nodes(nodes);
        self.addonFullTitle(addonFullTitle);


        /** Pop up confirm dialog for removing addon access for one project */
        self.removeNodeAuth = function(currNode) {
            bootbox.confirm({
                title: 'Deauthorize Dropbox for this project?',
                message: 'Are you sure you want to remove this Dropbox authorization?',
                callback: function(confirmed) {
                    if (confirmed) {
                        return sendDeauthorizeNode(currNode);
                    }
                }
            });
        };

        /** Send DELETE request to remove addon auth from a project */
        function sendDeauthorizeNode(currNode) {
            //TODO(asmacdo) dedropbox
            var api_url = currNode['api_url'] + 'dropbox/config/'
            console.log(api_url);


            return $.ajax({
                url: api_url,
                type: 'DELETE',
                success: function() {
                    self.nodes.remove(currNode)
                },
                error: function() {
                    self.changeMessage('Could not deauthorize because of an error. Please try again later.',
                        'text-danger');

                }
            });
        }
    }

    function AddonUserConfig(url) {
        var self = this;
        self.url = url;
        self.addons = ko.observableArray();

        $.ajax({

            url: url, type: 'GET', dataType: 'json',
            success: function(response) {
                var data = response.addons;
                data.forEach(function(addon) {
                    self.addons.push(new PermissionsViewModel(addon.full_name, addon.nodes));
                })
            },
            error: function(xhr, textStatus, error){
                console.error(textStatus); console.error(error);
                self.changeMessage('Could not retrieve settings. Please refresh the page or ' +
                    'contact <a href="mailto: support@cos.io">support@cos.io</a> if the ' +
                    'problem persists.', 'text-warning');
            }
        });
    }

    return AddonUserConfig;
}));