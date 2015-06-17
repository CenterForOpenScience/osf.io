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

function registration_failed() {
    $osf.unblock();
    bootbox.alert('Registration failed');
}

function draftNode(data) {

    // Block UI until request completes
    $osf.block();

    // POST data
    $.ajax({
        url:  ctx.node.urls.api + 'register/' + ctx.regTemplate + '/',
        type: 'POST',
        data: JSON.stringify(data),
        contentType: 'application/json',
        dataType: 'json'
    }).done(function(response) {
        if (response.status === 'success') {
            window.location.href = response.result;
        }
        else if (response.status === 'error') {
            registration_failed();
        }
    }).fail(function() {
        registration_failed();
    });

    // Stop event propagation
    return false;

}

(function() {
    var $editor = document.getElementById('editor');

    var proj_info, your_info, interesting, init_proj_info, init_your_info, init_interesting; 
    var init_array = [];
    var init_schemas = [];
    var prereg = [];
    var prereg_data = [];
    var titles = [];
    var editor;

    init_proj_info = [
        {
            name: "Project 1",
            year: 2015,
            publish_status: "unpublished"
        }
    ];

    init_your_info = [
        {
            name: "Bob Barker",
            age: 25,
            relationship_status: "single"
        }
    ];

    init_interesting = [
        {
            secrets: "I have no secrets.",
            upload_file: "",
            wiki: ""
        }
    ];

     prereg_data = [
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

    // initial data
    init_array.push(init_proj_info);
    init_array.push(init_your_info);
    init_array.push(init_interesting);

    init_array = prereg_data;

    prereg = [
        {
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
    

    proj_info = {
        title: "Project Info",
        type: "object",
        properties: {
            name: {
                type: "string",
                description: "Name of project",
                minLength: 3,
                //default: "Project 1"
            },
            year: {
                type: "integer",
                //default: 2015,
                minimum: 1900,
                maximum: 2016
            },
            publish_status: {
                type: "string",
                title: "publish status",
                //default: "unpublished"
            }
        }
    };

    your_info = {
        title: "Your Info",
        type: "object",
        properties: {
            name: {
                type: "string",
                description: "First and Last name",
                minLength: 3,
                //default: "Bob Barker"
            },
            age: {
                type: "integer",
                //default: 25,
                minimum: 5,
                maximum: 105
            },
            relationship_status: {
                type: "string",
                title: "relationship status",
                //default: "single"
            }
        }
    };

    interesting = {
        title: "Interesting Questions",
        type: "object",
        properties: {
            secrets: {
                type: "string",
                description: "Enter your most valued secret",
                minLength: 3,
                //default: "I have no secrets."
            },
            upload_file: {
                title: "upload file",
                type: "string",
                format: "url",
                options: {
                    upload: true
                },
                "links": [{
                    "href": "{{self}}"
                }]
            },
            wiki: {
                type: "string",
                format: "markdown"
            }
        }
    };

    // schemas for pagination
    init_schemas.push(proj_info);
    init_schemas.push(your_info);
    init_schemas.push(interesting);

    init_schemas = prereg;

    //var str = JSON.stringify(prereg);
    //console.log(str);
    //console.log(JSON.parse(str));

    var loadData = function(schemas, arrays) {
        // incorrect data input
        if (schemas.length !== arrays.length) {
            alert("The amount of data is inconsistent. Unable to load.");
            return;
        } if (schemas.length <= 0) {
            alert("There is no data to load.");
            return;
        }

        // load nav bar
        var tabs = '<li><a id="prev" href="#" aria-label="Previous"><span aria-hidden="true">&laquo;</span></a></li>';
        var pages;
        for (pages in init_schemas) {
            titles.push(init_schemas[pages].title);
            tabs = tabs + '<li><a id="tab' + pages + '" href="#">' + init_schemas[pages].title + '</a></li>';
        }

        tabs = tabs + '<li><a id="next" href="#" aria-label="Next"><span aria-hidden="true">&raquo;</span></a></li>';

        document.getElementById("myNavBar").innerHTML = tabs;

        // load the data for the first schema and display
        if(editor) editor.destroy();
        editor = new JSONEditor($editor,{
            schema: schemas[0],
            theme: 'bootstrap3',
            disable_collapse: true,
            disable_edit_json: true,
            disable_properties: true
        });
        editor.setValue(arrays[0]);
        window.editor = editor;
    };

    loadData(init_schemas, init_array);

    var reload = function(schemas, arrays, num) {
        if(editor) editor.destroy();
        editor = new JSONEditor($editor,{
            schema: schemas[num],
            theme: 'bootstrap3',
            disable_collapse: true,
            disable_edit_json: true,
            disable_properties: true
        });
        editor.setValue(arrays[num]);
        window.editor = editor;
    };

    JSONEditor.defaults.options.upload = function(type, file, cbs) {
        if (type === 'root.upload_fail') cbs.failure('Upload failed');
        else {
            var tick = 0;
            var tickFunction = function() {
                tick += 1;
                console.log('progress: ' + tick);
                if (tick < 100) {
                    cbs.updateProgress(tick);
                    window.setTimeout(tickFunction, 50)
                } else if (tick == 100) {
                    cbs.updateProgress();
                    window.setTimeout(tickFunction, 500)
                } else {
                    cbs.success('http://www.example.com/images/' + file.name);
                }
            };
            window.setTimeout(tickFunction)
        }
    };

    $(document.body).on('click', 'a', function() {
        var index = 0;
        var clicked = this.id;
        if (clicked === 'prev') {
            index = titles.indexOf(editor.options.schema.title);
            if (index === 0) {
                reload(init_schemas, init_array, 0);
            } else {
                reload(init_schemas, init_array, parseInt(index) - 1); 
            }
        } else if (clicked === 'next') {
            index = titles.indexOf(editor.options.schema.title);
            var max = init_schemas.length - 1;
            if (index === max) {
                reload(init_schemas, init_array, max);
            } else {
                reload(init_schemas, init_array, parseInt(index) + 1); 
            }
            
        } else {
            var id = clicked.split("tab");
            reload(init_schemas, init_array, id[1]);
        }
        
    });

    document.getElementById('save').onclick = function () {
        console.log(editor.options.schema.title);
        var schema;
        for (schema in init_schemas) {
            if (init_schemas[schema].title === editor.options.schema.title) {
                init_array[schema] = editor.getValue();
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

    // console.log("Test");

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
