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

function registerNode(data) {

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
    JSONEditor.plugins.epiceditor.basePath = 'epiceditor';

    var proj_info, your_info, interesting, init_proj_info, init_your_info, init_interesting; 
    var init_array = [];
    var init_schemas = [];
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

    // initial data
    init_array.push(init_proj_info);
    init_array.push(init_your_info);
    init_array.push(init_interesting);

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

    var loadData = function(schemas, arrays) {
        // incorrect data input
        if (schemas.length !== arrays.length) {
            alert("The amount of data is inconsistent. Unable to load.");
            return;
        } if (schemas.length <= 0) {
            alert("There is no data to load.");
            return;
        }

        // load the data for the first schema and display
        if(editor) editor.destroy();
        editor = new JSONEditor($editor,{
            schema: schemas[0],
            theme: 'bootstrap3',
            disable_collapse: true,
            disable_edit_json: true,
            disable_properties: true
        });
        editor.setValue(arrays[0][0]);
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
        editor.setValue(arrays[num][0]);
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

    editor.on('change',function() {
        for (schema in init_schemas) {
          if (init_schemas[schema].title === editor.options.schema.title) {
            init_array[schema][0] = editor.getValue();
          }
        }    
    });

    document.getElementById('project_info_button').onclick = function () {
        reload(init_schemas, init_array, 0);
    };

    document.getElementById('your_info_button').onclick = function () {
        reload(init_schemas, init_array, 1);
    };

    document.getElementById('interesting_button').onclick = function () {
        reload(init_schemas, init_array, 2);
        //reload(interesting, editor.getValue() || init_interesting);
        JSONEditor.plugins.epiceditor.basePath = 'epiceditor';
    };

    document.getElementById('next').onclick = function () {
        console.log(editor);
        for (schema in init_schemas) {
            if (init_schemas[schema].title === editor.options.schema.title) {

                if (parseInt(schema) == (init_schemas.length - 1)) {
                    reload(init_schemas, init_array, schema);
                } else {
                    console.log(parseInt(schema) + 1);
                    reload(init_schemas, init_array, parseInt(schema) + 1);
                }
            }
        } 
    };

    document.getElementById('prev').onclick = function () {
        reload(init_schemas, init_array, 1);
    };

    document.getElementById('save').onclick = function () {
        //console.log(editor.getValue());
        for (schema in init_schemas) {
            if (init_schemas[schema].title === editor.options.schema.title) {
                init_array[schema][0] = editor.getValue();
            }
        } 
    };

})();

$(document).ready(function() {

    // Don't submit form on enter; must use $.delegate rather than $.on
    // to catch dynamically created form elements
    $('#registration_template').delegate('input, select', 'keypress', function(event) {
        return event.keyCode !== 13;
    });

    var registrationViewModel = new MetaData.ViewModel(
        ctx.regSchema,
        ctx.registered,
        [ctx.node.id].concat(ctx.node.children)
    );
    // Apply view model
    ko.applyBindings(registrationViewModel, $('#registration_template')[0]);
    registrationViewModel.updateIdx('add', true);

    if (ctx.registered) {
        registrationViewModel.unserialize(ctx.regPayload);
    }

    $('#registration_template form').on('submit', function() {

        // Serialize responses
        var serialized = registrationViewModel.serialize(),
            data = serialized.data,
            complete = serialized.complete;

        // Clear continue text and stop if incomplete
        if (!complete) {
            registrationViewModel.continueText('');
            return false;
        }

        $.ajax({
            url: ctx.node.urls.api + 'beforeregister/',
            contentType: 'application/json',
            success: function(response) {
                if (response.prompts && response.prompts.length) {
                    bootbox.confirm(
                        $osf.joinPrompts(response.prompts, 'Are you sure you want to register this project?'),
                        function(result) {
                            if (result) {
                                registerNode(data);
                            }
                        }
                    );
                } else {
                    registerNode(data);
                }
            }
        });

        return false;

    });
});
