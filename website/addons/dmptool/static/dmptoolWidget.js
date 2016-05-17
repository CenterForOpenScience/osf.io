'use strict';
var ko = require('knockout');
var $ = require('jquery');

var $osf = require('js/osfHelpers');
var language = require('js/osfLanguage').Addons.dmptool;



function ViewModel(url) {
    var self = this;

    self.url = url;
    self.connected = ko.observable();

    // self.dmptool = ko.observable();
    // self.dmptoolUrl = ko.observable();
    // self.dataset = ko.observable();
    // self.doi = ko.observable();
    // self.datasetUrl = ko.observable('');
    // self.citation = ko.observable('');

    self.loaded = ko.observable(false);

    self.plans = ko.observableArray();

    // current plan
    self.plan_id = ko.observable();
    self.plan_name = ko.observable();
    self.plan_created = ko.observable();
    self.plan_requirements = ko.observableArray();
    self.plan_pdf = ko.observable();
    self.plan_docx = ko.observable();

    // Flashed messages
    self.message = ko.observable('');
    self.messageClass = ko.observable('text-info');

    self.init = function() {
        $.ajax({
            url: url, type: 'GET', dataType: 'json',
            success: function(response) {
                var data = response.data;
                self.connected(data.connected);

                self.plans(data.plans);

                self.loaded(true);
            },
            error: function(xhr) {
                self.loaded(true);
                var errorMessage = (xhr.status === 403) ? language.widgetInvalid : language.widgetError;
                self.changeMessage(errorMessage, 'text-danger');
            }
        });
    };

    /** Change the flashed status message */
    self.changeMessage = function(text, css, timeout) {
        self.message(text);
        var cssClass = css || 'text-info';
        self.messageClass(cssClass);
        if (timeout) {
            // Reset message after timeout period
            setTimeout(function() {
                self.message('');
                self.messageClass('text-info');
            }, timeout);
        }
    };

    self.renderPlan = function (plan) {

        console.log('renderPlan');
        self.plan_id(plan.id);

        // console.log(plan.id);
        // console.log(self.url);
        // console.log(plan.get_plan_url);

        $.ajax({
            url: plan.get_plan_url, type: 'GET', dataType: 'json',
            success: function(response) {
                //console.log(response.plan);
                //self.plan(response.plan);
                plan = response.plan;
                console.log(plan);
                self.plan_name(plan.name);
                self.plan_created(plan.created);
                self.plan_pdf(plan.pdf_url);
                self.plan_docx(plan.docx_url);

                // loop through requirements
                self.plan_requirements.removeAll();
                console.log(plan.template.requirements.length);
                for (var i = 0, len = plan.template.requirements.length; i < len; i++) {
                    //console.log(plan.template.requirements[i]);
                    var requirement = plan.template.requirements[i].requirement;
                    //console.log(requirement);
                    self.plan_requirements.push(
                       {
                        'text_brief': requirement.text_brief,
                        'response': requirement.response
                       }
                    )
                }
                //console.log(self.plan_requirements());

            },
            error: function(xhr) {
                $("#dmptool-output").html("error");
            }

        });

        
    }
}

// Public API
function DmptoolWidget(selector, url) {
    var self = this;
    self.viewModel = new ViewModel(url);
    $osf.applyBindings(self.viewModel, selector);
    self.viewModel.init();
}

module.exports = DmptoolWidget;
