'use strict';
var $ = require('jquery');
var ko = require('knockout');
var bootbox = require('bootbox');
var $osf = require('js/osfHelpers');
var jedit = require('json-editor');

var MetaData = require('../metadata_1.js');
var ctx = window.contextVars;
/**
    * Unblock UI and display error modal
    */

(function() {
    var $editor = document.getElementById('editor');
 
    var schema_data = [];
    var init_schemas = [];
    var prereg = [];
    var open_ended = [];
    var titles = [];
    var editor;

     schema_data = [
        {
            item1: "an answer",
            item2: "an answer",
            item3: "an answer",
            item4: "an answer",
            item5: "an answer",
            item6: "an answer",
            item7: "an answer",
            item8: "an answer",
            item9: "an answer",
            summary: "a summary",
        },
        {
            item10: "yes",
            item11: "an answer",
            item12: "an answer",
            item13: "an answer",
            item14: "an answer",
            item15: "an answer",
            item16: "an answer",
        },
        {

            item17: "Exact",
            item18: "Exact",
            item19: "Exact",
            item20: "Exact",
            item21: "Exact",
            item22: "Exact",
            item23: "Exact",
            item24: "an answer",
            item25: "an answer",
        },
        {
            item26: "an answer",
            item27: "an answer",
            item28: "an answer",
        }
    ];

    open_ended = [
        {
            id: "Open-Ended_Registration",
            title: "Open Ended Registration",
            type: "object",
            properties: {           
                summary: {
                    type: "string",
                    format: "textarea",
                    title: "Provide a narrative summary of what is contained in this registration, or how it differs from prior registrations."
                }          
            }
        }

    ];

    prereg = [
        {
            id: "Replication_Recipe_(Brandt_et_al.,_2013):_Pre-Registration",
            title: "The Nature of the Effect",
            type: "object",
            properties: {
                item1: {
                   type: "string", title: "Verbal description of the effect I am trying to replicate" 
                },
                item2: {
                    type: "string", title: "It is important to replicate this effect because"
                },
                item3: {
                    type: "string", title: "The effect size of the effect I am trying to replicate is"
                },
                item4: {
                    type: "string", title: "The confidence interval of the original effect is"
                },
                item5: {
                    type: "string", title: "The sample size of the original effect is"
                },
                item6: {
                    type: "string", title: "Where was the original study conducted? (e.g., lab, in the field, online)"
                },
                item7: {
                    type: "string", title: "What country/region was the original study conducted in?"
                },
                item8: {
                    type: "string", title: "What kind of sample did the original study use? (e.g., student, Mturk, representative)"
                },
                item9: {
                    type: "string", title: "Was the original study conducted with paper-and-pencil surveys, on a computer, or something else?"
                }
            }
        },
        {
            title: "Designing the Replication Study",
            type: "object",
            properties: {
                item10: {
                    type: "string", title: "Are the original materials for the study available from the author?", enum: ["yes", "no"], description: "Choose..."
                },
                item11: {
                    type: "string", title: "I know that assumptions (e.g., about the meaning of the stimuli) in the original study will also hold in my replication because"
                },
                item12: {
                    type: "string", title: "Location of the experimenter during data collection"
                },
                item13: {
                    type: "string", title: "Experimenter knowledge of participant experimental condition"
                },
                item14: {
                    type: "string", title: "Experimenter knowledge of overall hypotheses"
                },
                item15: {
                    type: "string", title: "My target sample size is"
                },
                item16: {
                    type: "string", title: "The rationale for my sample size is"
                }
            }
        },
        {
            title: "Documenting Differences between the Original and Replication Study",
            type: "object",
            properties: {
                item17: {
                    type: "string", title: "The similarities/differences in the instructions are", enum: ["Exact", "Close", "Different"], description: "Choose..."
                },
                item18: {
                    type: "string", title: "The similarities/differences in the measures are", enum: ["Exact", "Close", "Different"], description: "Choose..."
                },
                item19: {
                    type: "string", title: "The similarities/differences in the stimuli are", enum: ["Exact", "Close", "Different"], description: "Choose..."
                },
                item20: {
                    type: "string", title: "The similarities/differences in the procedure are", enum: ["Exact", "Close", "Different"], description: "Choose..."
                },
                item21: {
                    type: "string", title: "The similarities/differences in the location (e.g., lab vs. online; alone vs. in groups) are", enum: ["Exact", "Close", "Different"], description: "Choose..."
                },
                item22: {
                    type: "string", title: "The similarities/difference in remuneration are", enum: ["Exact", "Close", "Different"], description: "Choose..."
                },
                item23: {
                    type: "string", title: "The similarities/differences between participant populations are", enum: ["Exact", "Close", "Different"], description: "Choose..."
                },
                item24: {
                    type: "string", title: "What differences between the original study and your study might be expected to influence the size and/or direction of the effect?"
                },
                item25: {
                    type: "string", title: "I have taken the following steps to test whether the differences listed in the previous question will influence the outcome of my replication attempt"
                }
            }
        },
        {
            title: "Analysis and Replication Evaluation",
            type: "object",
            properties: {
                item26: {
                    type: "string", title: "My exclusion criteria are (e.g., handling outliers, removing participants from analysis)"
                },
                item27: {
                    type: "string", title: "My analysis plan is (justify differences from the original)"
                },
                item28: {
                    type: "string", title: "A successful replication is defined as"
                }
            }
        }
    ];

    // all schemas are in one array of arrays
    init_schemas.push(open_ended);
    init_schemas.push(prereg);

    var which_schema = 0;

    // this is how the import and export should work
    //var str = JSON.stringify(prereg);
    //console.log(str);
    //console.log(JSON.parse(str));

    var loadData = function(schemas, arrays, which) {
        // incorrect data input
        if (schemas[which].length > arrays.length) {
            alert("The amount of data is inconsistent. Unable to load.");
            return;
        } if (schemas[which].length <= 0) {
            alert("There is no data to load.");
            return;
        }

        // load nav bar -- need to account for situations when there is only one page (take away prev and next)
        var tabs = '<li><a id="prev" href="#" aria-label="Previous"><span aria-hidden="true">&laquo;</span></a></li>';
        var pages;
        for (pages in schemas[which]) {
            titles.push(schemas[which][pages].title);
            tabs = tabs + '<li><a id="tab' + pages + '" href="#">' + schemas[which][pages].title + '</a></li>';
        }

        tabs = tabs + '<li><a id="next" href="#" aria-label="Next"><span aria-hidden="true">&raquo;</span></a></li>';

        document.getElementById("myNavBar").innerHTML = tabs;

        // load the data for the first schema and display
        if(editor) editor.destroy();
        editor = new JSONEditor($editor,{
            schema: schemas[which][0],
            theme: 'bootstrap3',
            disable_collapse: true,
            disable_edit_json: true,
            disable_properties: true,
            no_additional_properties: true
        });
        editor.setValue(arrays[0]);
        window.editor = editor;
    };

    // where the array of schemas and array of data is held
    loadData(init_schemas, schema_data, 0);

    // called when switches pages
    var reload = function(schemas, data, num, which) {
        if(editor) editor.destroy();
        editor = new JSONEditor($editor,{
            schema: schemas[which][num],
            theme: 'bootstrap3',
            disable_collapse: true,
            disable_edit_json: true,
            disable_properties: true,
            no_additional_properties: true
        });
        editor.setValue(data[num]);
        window.editor = editor;
    };


    // need to update so that it doesn't register when the top nav bar is clicked
    $(document.body).on('click', 'a', function() {
        var index = 0;
        var clicked = this.id;
        if (clicked === 'prev') {
            index = titles.indexOf(editor.options.schema.title);
            if (index === 0) {
                reload(init_schemas, schema_data, 0, which_schema);
            } else {
                reload(init_schemas, schema_data, parseInt(index) - 1, which_schema); 
            }
        } else if (clicked === 'next') {
            index = titles.indexOf(editor.options.schema.title);
            var max = init_schemas.length - 1;
            if (index === max) {
                reload(init_schemas, schema_data, max, which_schema);
            } else {
                reload(init_schemas, schema_data, parseInt(index) + 1, which_schema); 
            }
            
        } else {
            var id = clicked.split("tab");
            reload(init_schemas, schema_data, id[1], which_schema);
        }

        // this doesn't really work...needs to add query string to url without page refresh
        //window.history.pushState('container', editor.options.schema.title, window.location.href + '?' + editor.options.schema.title);
        
    });

    // get schema that was selected by user
    $(document.body).on('change', "#select-registration-template", function() {
        var $tempName = '';
        var $this = $(this);
        var val = $this.val();
        if (val !== '') {
            document.getElementById("title").innerHTML = val;

            var schema;
            for (schema in init_schemas) {
                if (init_schemas[schema][0].id === val) {
                    which_schema = schema;
                    loadData(init_schemas, schema_data, which_schema);
                } 
            }
            
            //reload(init_schemas, schema_data, 0);
        } else {
            document.getElementById("title").innerHTML = "Select an option above";
        }
    });

    document.getElementById('save').onclick = function () {
        console.log(editor.options.schema.title);
        var schema;
        for (schema in init_schemas) {
            if (init_schemas[schema].title === editor.options.schema.title) {
                schema_data[schema] = editor.getValue();
            }
        } 
    };

})();

$(document).ready(function() {

    // $.ajax({
    //     url: ctx.node.urls.api + 'beforedraft/',
    //     contentType: 'application/json',
    //     success: function(response) {
    //         if (response.prompts && response.prompts.length) {
    //             bootbox.confirm(
    //                 $osf.joinPrompts(response.prompts, 'Are you sure you want to create a draft of this project?'),
    //                 function(result) {
    //                     if (result) {
    //                         draftNode(data);
    //                     }
    //                 }
    //             );
    //         } else {
    //             draftNode(data);
    //         }
    //     }
    // });


    // Don't submit form on enter; must use $.delegate rather than $.on
    // to catch dynamically created form elements
    // $('#registration_template').delegate('input, select', 'keypress', function(event) {
    //     return event.keyCode !== 13;
    // });

    // var registrationViewModel = new MetaData.ViewModel(
    //     ctx.regSchema,
    //     ctx.registered,
    //     [ctx.node.id].concat(ctx.node.children)
    // );
    // // Apply view model
    // ko.applyBindings(registrationViewModel, $('#registration_template')[0]);
    // registrationViewModel.updateIdx('add', true);

    // if (ctx.registered) {
    //     registrationViewModel.unserialize(ctx.regPayload);
    // }

    // $('#registration_template form').on('submit', function() {

    //     // Serialize responses
    //     var serialized = registrationViewModel.serialize(),
    //         data = serialized.data,
    //         complete = serialized.complete;

    //     // Clear continue text and stop if incomplete
    //     if (!complete) {
    //         registrationViewModel.continueText('');
    //         return false;
    //     }

    //     $.ajax({
    //         url: ctx.node.urls.api + 'beforeregister/',
    //         contentType: 'application/json',
    //         success: function(response) {
    //             if (response.prompts && response.prompts.length) {
    //                 bootbox.confirm(
    //                     $osf.joinPrompts(response.prompts, 'Are you sure you want to register this project?'),
    //                     function(result) {
    //                         if (result) {
    //                             registerNode(data);
    //                         }
    //                     }
    //                 );
    //             } else {
    //                 registerNode(data);
    //             }
    //         }
    //     });

    // $(document).ready(function() {

    // $.ajax({
    //     url: ctx.node.urls.api + 'beforerdraft/',
    //     contentType: 'application/json',
    //     success: function(response) {
    //         if (response.prompts && response.prompts.length) {
    //             bootbox.confirm(
    //                 $osf.joinPrompts(response.prompts, 'Are you sure you want to create a draft of this project?'),
    //                 function(result) {
    //                     if (result) {
    //                         draftNode(data);
    //                     }
    //                 }
    //             );
    //         } else {
    //             draftNode(data);
    //         }
    //     }
    // });

    //     return false;

    // });
});
