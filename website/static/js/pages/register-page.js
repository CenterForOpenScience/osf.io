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
    document.getElementById('save').style.visibility = 'hidden';
 
    var schema_data = [];
    var init_schemas = [];
    var prereg = [];
    var open_ended = [];
    var postcomp = [];
    var osf_stand = [];
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
            item29: "an answer",
            datacompletion: "yes",
            looked: "yes",
            comments: "an answer",
        },
        {
            item10: "yes",
            item11: "an answer",
            item12: "an answer",
            item13: "an answer",
            item14: "an answer",
            item15: "an answer",
            item16: "an answer",
            item30: "an answer",
            item31: "an answer",
            item32: "significantly different from the original effect size",
            item33: "success",
            item34: "an answer",
            item35: "an answer",
            item36: "an answer",
            item37: "an answer",

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
            title: "Open Ended",
            type: "object",
            properties: {           
                summary: {
                    type: "string",
                    format: "textarea",
                    title: "Provide a narrative summary of what is contained in this registration, or how it differs from prior registrations."
                }          
            },
            category: "draft",
        }

    ];

    osf_stand = [
        {
            id: "OSF-Standard_Pre-Data_Collection_Registration",
            title: "Pre-Data Collection",
            type: "object",
            properties: {
                datacompletion: {
                    type: "array",
                    title: "Is data collection for this project underway or complete?",
                    uniqueItems: true,
                    items: {
                        type: "string",
                        enum: ["yes", "no"],
                    },
                    description: "Choose..."
                },
                looked: {
                    type: "array",
                    title: "Have you looked at the data?",
                    uniqueItems: true,
                    items: {
                        type: "string",
                        enum: ["yes", "no"],
                    },
                    description: "Choose..."
                },
                comments: {
                    type: "string",
                    format: "textarea",
                    title: "Other Comments"
                }
            },
            category: "draft",
        }
    ];

    postcomp = [
        {
            id: "Replication_Recipe_(Brandt_et_al.,_2013):_Post-Completion",
            title: "Registering the Replication Attempt",
            type: "object",
            properties: {
                item29: {
                    type: "string", format: "text", title: "The finalized materials, procedures, analysis plan etc of the replication are registered here"
                }
            },
            category: "draft",
        },
        {  
            title: "Reporting the Replication",
            type: "object",
            properties: {
                item30: {
                    type: "string", format: "text", title: "The effect size of the replication is"
                },
                item31: {
                    type: "string", format: "text", title: "The confidence interval of the replication effect size is"
                },
                item32: {
                    type: "array", title: "The replication effect size is",
                    uniqueItems: true,
                    items: {
                        type: "string",
                        enum: ["significantly different from the original effect size", "not significantly different from the original effect size"], 
                    },
                    description: "Choose..."
                },
                item33: {
                    type: "array", 
                    title: "I judge the replication to be a(n)", 
                    uniqueItems: true,
                    items: {
                        type: "string",
                        enum: ["success", "informative failure to replicate", "practical failure to replicate", "inconclusive"],
                    },
                    description: "Choose..."
                },
                item34: {
                    type: "string", format: "textarea", title: "I judge it so because"
                },
                item35: {
                    type: "string", format: "text", title: "Interested experts can obtain my data and syntax here"
                },
                item36: {
                    type: "string", format: "text", title: "All of the analyses were reported in the report or are available here"
                },
                item37: {
                    type: "string", format: "textarea", title: "The limitations of my replication study are"
                }
            },
            category: "draft",
        }      

    ]

    prereg = [
        {
            id: "Replication_Recipe_(Brandt_et_al.,_2013):_Pre-Registration",
            title: "The Nature of the Effect",
            type: "object",
            properties: {
                item1: {
                   type: "string", format: "textarea", title: "Verbal description of the effect I am trying to replicate" 
                },
                item2: {
                    type: "string", format: "textarea", title: "It is important to replicate this effect because"
                },
                item3: {
                    type: "string", format: "text", title: "The effect size of the effect I am trying to replicate is"
                },
                item4: {
                    type: "string", format: "text", title: "The confidence interval of the original effect is"
                },
                item5: {
                    type: "string", format: "text", title: "The sample size of the original effect is"
                },
                item6: {
                    type: "string", format: "text", title: "Where was the original study conducted? (e.g., lab, in the field, online)"
                },
                item7: {
                    type: "string", format: "text", title: "What country/region was the original study conducted in?"
                },
                item8: {
                    type: "string", format: "text", title: "What kind of sample did the original study use? (e.g., student, Mturk, representative)"
                },
                item9: {
                    type: "string", format: "text", title: "Was the original study conducted with paper-and-pencil surveys, on a computer, or something else?"
                }
            },
            category: "draft",
        },
        {
            title: "Designing the Replication Study",
            type: "object",
            properties: {
                item10: {
                    type: "array", title: "Are the original materials for the study available from the author?",
                    uniqueItems: true,
                    items: {
                        type: "string",
                        enum: ["yes", "no"], 
                    },
                    description: "Choose..."
                },
                item11: {
                    type: "string", format: "textarea", title: "I know that assumptions (e.g., about the meaning of the stimuli) in the original study will also hold in my replication because"
                },
                item12: {
                    type: "string", format: "text", title: "Location of the experimenter during data collection"
                },
                item13: {
                    type: "string", format: "text", title: "Experimenter knowledge of participant experimental condition"
                },
                item14: {
                    type: "string", format: "text", title: "Experimenter knowledge of overall hypotheses"
                },
                item15: {
                    type: "string", format: "text", title: "My target sample size is"
                },
                item16: {
                    type: "string", format: "textarea", title: "The rationale for my sample size is"
                }
            },
            category: "draft",
        },
        {
            title: "Documenting Differences between the Original and Replication Study",
            type: "object",
            properties: {
                item17: {
                    type: "array", title: "The similarities/differences in the instructions are",
                    uniqueItems: true,
                    items: {
                        type: "string",
                        enum: ["Exact", "Close", "Different"],
                    },
                    description: "Choose..."
                },
                item18: {
                    type: "array", title: "The similarities/differences in the measures are", 
                    uniqueItems: true,
                    items: {
                        type: "string",
                        enum: ["Exact", "Close", "Different"],
                    },
                    description: "Choose..."
                },
                item19: {
                    type: "array", title: "The similarities/differences in the stimuli are", 
                    uniqueItems: true,
                    items: {
                        type: "string",
                        enum: ["Exact", "Close", "Different"],
                    },
                    description: "Choose..."
                },
                item20: {
                    type: "array", title: "The similarities/differences in the procedure are", 
                    uniqueItems: true,
                    items: {
                        type: "string",
                        enum: ["Exact", "Close", "Different"],
                    },
                    description: "Choose..."
                },
                item21: {
                    type: "array", title: "The similarities/differences in the location (e.g., lab vs. online; alone vs. in groups) are", 
                    uniqueItems: true,
                    items: {
                        type: "string",
                        enum: ["Exact", "Close", "Different"],
                    },
                    description: "Choose..."
                },
                item22: {
                    type: "array", title: "The similarities/difference in remuneration are", 
                    uniqueItems: true,
                    items: {
                        type: "string",
                        enum: ["Exact", "Close", "Different"],
                    },
                    description: "Choose..."
                },
                item23: {
                    type: "array", title: "The similarities/differences between participant populations are", 
                    uniqueItems: true,
                    items: {
                        type: "string",
                        enum: ["Exact", "Close", "Different"],
                    },
                    description: "Choose..."
                },
                item24: {
                    type: "string", format: "textarea", title: "What differences between the original study and your study might be expected to influence the size and/or direction of the effect?"
                },
                item25: {
                    type: "string", format: "textarea", title: "I have taken the following steps to test whether the differences listed in the previous question will influence the outcome of my replication attempt"
                }
            },
            category: "draft",
        },
        {
            title: "Analysis and Replication Evaluation",
            type: "object",
            properties: {
                item26: {
                    type: "string", format: "textarea", title: "My exclusion criteria are (e.g., handling outliers, removing participants from analysis)"
                },
                item27: {
                    type: "string", format: "textarea", title: "My analysis plan is (justify differences from the original)"
                },
                item28: {
                    type: "string", format: "textarea", title: "A successful replication is defined as"
                }
            },
            category: "draft",
        }
    ];

    // all schemas are in one array of arrays
    init_schemas.push(open_ended);
    init_schemas.push(prereg);
    init_schemas.push(postcomp);
    init_schemas.push(osf_stand);

    var which_schema = 0;

    // this is how the import and export should work
    //var str = JSON.stringify(osf_stand);
    //console.log(str);
    //console.log(JSON.parse(str));

    // add for single select of check boxes
    JSONEditor.defaults.resolvers.unshift(function(schema) {
        if(schema.type === "array" && schema.items && !(Array.isArray(schema.items)) && schema.uniqueItems && schema.items["enum"] && ['string','number','integer'].indexOf(schema.items.type) >= 0) {
             return "singleselect";       
        }    
    });

    JSONEditor.defaults.editors.singleselect = JSONEditor.defaults.editors.multiselect.extend({      
        build: function() {
            
            var self = this, i;
            if(!this.options.compact) this.header = this.label = this.theme.getFormInputLabel(this.getTitle());
            if(this.schema.description) this.description = this.theme.getFormInputDescription(this.schema.description);

            if((!this.schema.format && this.option_keys.length < 8) || this.schema.format === "checkbox") {
              this.input_type = 'checkboxes';

              this.inputs = {};
              this.controls = {};
              for(i=0; i<this.option_keys.length; i++) {
                this.inputs[this.option_keys[i]] = this.theme.getCheckbox();
                this.select_options[this.option_keys[i]] = this.inputs[this.option_keys[i]];
                var label = this.theme.getCheckboxLabel(this.option_keys[i]);
                this.controls[this.option_keys[i]] = this.theme.getFormControl(label, this.inputs[this.option_keys[i]]);
              }

              this.control = this.theme.getMultiCheckboxHolder(this.controls,this.label,this.description);
            }
            else {
              this.input_type = 'select';
              this.input = this.theme.getSelectInput(this.option_keys);
              this.input.multiple = true;
              this.input.size = Math.min(10,this.option_keys.length);

              for(i=0; i<this.option_keys.length; i++) {
                this.select_options[this.option_keys[i]] = this.input.children[i];
              }

              if(this.schema.readOnly || this.schema.readonly) {
                this.always_disabled = true;
                this.input.disabled = true;
              }

              this.control = this.theme.getFormControl(this.label, this.input, this.description);
            }
            
            this.container.appendChild(this.control);
            var previous;
            this.control.addEventListener("mouseover", function(e) {
                var new_value = [];
                for(i = 0; i<self.option_keys.length; i++) {
                    if(self.select_options[self.option_keys[i]].selected || self.select_options[self.option_keys[i]].checked) {
                        new_value.push(self.select_values[self.option_keys[i]]);
                    }
                }
                previous = new_value;
                   
            });
            this.control.addEventListener('change',function(e) {
              e.preventDefault();
              e.stopPropagation();

              // delete older one using previous
              var new_value = [];
                for(i = 0; i<self.option_keys.length; i++) {
                    if(self.select_options[self.option_keys[i]].selected || self.select_options[self.option_keys[i]].checked) {

                        var str = '"' + self.select_values[self.option_keys[i]] + '"';
                        var blah = self.select_values[self.option_keys[i]];
                        if (previous.indexOf(blah) != -1) {
                            self.select_options[self.option_keys[i]].checked = false;
                        }
                         else { 
                            new_value.push(self.select_values[self.option_keys[i]]);
                        }
                    }
                }
              self.updateValue(new_value);
              self.onChange(true);
            });
        },
    });

    var loadData = function(schemas, arrays, which) {
        titles = [];
        // incorrect data input
        if (schemas[which].length > arrays.length) {
            alert("The amount of data is inconsistent. Unable to load.");
            return;
        } if (schemas[which].length <= 0) {
            alert("There is no data to load.");
            return;
        }

        // load nav bar -- need to account for situations when there is only one page (take away prev and next)
        if (schemas[which].length > 1) {
            var tabs = '<nav><ul class="pagination"><li><a id="prev" href="#" aria-label="Previous"><span aria-hidden=true>&laquo;</span></a></li>';
            var pages;
            for (pages in schemas[which]) {
                //console.log(schemas[which][pages].category);
                titles.push(schemas[which][pages].title);
                tabs = tabs + '<li><a id="tab' + pages + '" href="#">' + schemas[which][pages].title + '</a></li>';
            }

            tabs = tabs + '<li><a id="next" href="#" aria-label="Next"><span aria-hidden=true>&raquo;</span></a></li></ul></nav>';

            document.getElementById("myNavBar").innerHTML = tabs;
        } else {
            document.getElementById("myNavBar").innerHTML = "";
        }
        
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
            var max = init_schemas[which_schema].length - 1;
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
        var $this = $(this);
        var val = $this.val();
        var tempName = val.replace(/_/g , " ");

        if (val !== '') {
            document.getElementById("title").innerHTML = tempName;

            var schema;
            for (schema in init_schemas) {
                if (init_schemas[schema][0].id === val) {
                    which_schema = schema;
                    loadData(init_schemas, schema_data, which_schema);
                } 
            }

            document.getElementById('save').style.visibility = 'visible';
            //reload(init_schemas, schema_data, 0);
        } else {
            document.getElementById("title").innerHTML = "Select an option above";
            document.getElementById('save').style.visibility = 'hidden';
            document.getElementById("myNavBar").innerHTML = "";
            document.getElementById("editor").innerHTML = "";

        }
    });

    document.getElementById('save').onclick = function () {
        var schema;
        var value;
        for (schema in init_schemas[which_schema]) {
            if (init_schemas[which_schema][schema].title === editor.options.schema.title) {
                for (value in editor.getValue()) {
                   schema_data[schema][value] = editor.getValue()[value];
                }
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
