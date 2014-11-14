(function(global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['knockout', 'jquery', 'osfutils'], factory);
    } else if(typeof $script === 'function') {
        global.AddonSelector = factory(ko, jQuery);
        $script.done('addonSelector');
    } else {
        global.AddonSelector = factory(ko, jQuery);
    }
}(this, function(ko, $) {
    'use strict';

    function AddonsViewModel(){
        var self = this;

        self.addonCategoryData = ko.observableArray([]);
        self.addonsEnabled = ko.observableArray([]);
        
        var checkedOnLoad = [];
        var nameMap = {};

        $.getJSON('/api/v1/settings/addons/', function(response){
            var data = response;
            self.addonsEnabled(data.addons_enabled);
            checkedOnLoad = data.addons_enabled.slice();

            data.addons_available.forEach(function(addon){
                nameMap[addon.short_name] = addon.full_name;
            });

            data.addon_categories.forEach(function(category){
                var addonList = [];
                data.addons_available.forEach(function(addon){
                    if (addon.categories.indexOf(category) > -1){
                        addonList.push({'ShortName': addon.short_name, 'FullName': addon.full_name});
                    }
                });
                if (typeof addonList !== 'undefined' && addonList.length > 0){
                    self.addonCategoryData.push({'Name': capitalize(category), 'Addons': addonList});
                }
            });

            $('form#selectAddonsForm').show();
        }); 
        


        self.submitAddons = function() {
            var unchecked = checkedOnLoad.filter(function(x ){return self.addonsEnabled().indexOf(x) < 0;});

            var submit = function() {
                var payload = {};
                for (var addon in nameMap){
                    payload[addon] = (self.addonsEnabled().indexOf(addon) >= 0);
                }

                var request = $.osf.postJSON('/api/v1/settings/addons/', payload);
                request.done(function() {
                    window.location.reload();
                });
                request.fail(function() {
                    var msg = 'Sorry, we had trouble saving your settings. If this persists please contact <a href="mailto: support@osf.io">support@osf.io</a>';
                    bootbox.alert({title: 'Request failed', message: msg});
                });
            };

            if(unchecked.length > 0) {
                var uncheckedText = unchecked.map(function(shortName){ 
                    return ['<li>', nameMap[shortName],'</li>'].join('');
                }).join('');
                uncheckedText = ['<ul>', uncheckedText, '</ul>'].join('');
                bootbox.confirm({
                    title: 'Are you sure you want to remove the add-ons you have deselected? ',
                    message: uncheckedText,
                    callback: function(result) {
                        if (result) {
                            submit();
                        } else{
                            self.addonsEnabled(checkedOnLoad.slice());
                        }
                    }
                });
            } else {
                submit();
            }
            return false;
        }; 
    }

    function AddonsModule(selector){
        this.AddonsViewModel = new AddonsViewModel();
        $.osf.applyBindings(this.AddonsViewModel, selector);
    }

    function capitalize(string){
        return string.charAt(0).toUpperCase() + string.slice(1);
    }

    return AddonsModule;
}));