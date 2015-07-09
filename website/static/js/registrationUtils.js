var $ = require('jquery');
var ko = require('knockout');
var bootbox = require('bootbox');
var moment = require('moment');
var URI = require('URIjs');

var $osf = require('js/osfHelpers');
var oop = require('js/oop');

require('js/registrationEditorExtensions');

var formattedDate = function(dateString) {
    if (!dateString) {
        return 'never';
    }
    var d = new Date(dateString);
    return moment(dateString).fromNow() + ' (' + d.toGMTString() + ')';
};

var currentUser = window.contextVars.currentUser || {
    id: null,
    name: 'Anonymous'
};


/** 
 * @class Comment
 * Model for storing/editing/deleting comments on form fields
 * 
 * @param {Object} data: optional data to instatiate model with
 * @param {User} data.user
 * @param {Date} data.lastModified
 * @param {String} data.value
 *
 * @type User
 * @property {String} id
 * @property {String} name
 **/
var Comment = function(data) {
    var self = this;

    self.saved = ko.observable(data ? true : false);

    data = data || {};
    self.user = data.user || currentUser;
    self.lastModified = moment(data.lastModified || new Date());
    self.value = ko.observable(data.value || '');

    /**
     * Returns 'You' if the current user is the commenter, else the commenter's name
     **/
    self.author = ko.pureComputed(function() {
        if (self.user.id === currentUser.id) {
            return 'You';
        }
        else {
            return self.user.name;
        }
    });

    /**
     * Returns true if the current user is the comment creator
     **/
    self.canDelete = ko.pureComputed(function() {
        return self.user.id === currentUser.id;
    });
    /**
     * Returns true if the comment is saved and the current user is the comment creator
     **/
    self.canEdit = ko.pureComputed(function() {
        return self.saved() && self.user.id === currentUser.id;
    });
};
// Let ENTER keypresses add a comment if comment <input> is in focus
$(document).keydown(function(e) {
    if (e.keyCode === 13) {
        $target = $(e.target);
        if ($target.hasClass('registration-editor-comment')) {
            var $button = $target.siblings('span').find('button');
            if(!$button.is(':disabled')) {
                $button.click();
            }
        }
    }
});

/**
 * @class Question
 * Model for schema questions 
 * 
 * @param {Object} data: optional instantiation values
 * @param {String} data.title
 * @param {String} data.nav: short version of title
 * @param {String} data.type: 'string' | 'number' | 'choose' | 'object'; data type
 * @param {String} data.format: 'text' | 'textarea' | 'list'; format corresponding with data.type
 * @param {String} data.description
 * @param {String} data.help
 * @param {String[]} data.options: array of options for 'choose' types
 * @param {Object[]} data.properties: object of sub-Question properties for 'object' types
 * @param {String} id: unique identifier
 **/
var Question = function(data, id) {
    var self = this;

    self.id = id || -1;

    self.value = ko.observable(data.value || null);
    self.setValue = function(val) {
        self.value(val);
    };

    self.title = data.title || 'Untitled';
    self.nav = data.nav || 'Untitled';
    self.type = data.type || 'string';
    self.format = data.format || 'text';
    self.description = data.description || '';
    self.help = data.help || 'no help text provided';
    self.options = data.options || [];
    self.properties = data.properties || {};
    self.match = data.match || '';

    self.showExample = ko.observable(false);

    self.comments = ko.observableArray(
        $.map(data.comments || [], function(comment) {
            return new Comment(comment);
        })
    );
    self.nextComment = ko.observable('');
    /**
     * @returns {Boolean} true if the nextComment <input> is not blank
     **/
    self.allowAddNext = ko.computed(function() {
        return !$osf.isBlank(self.nextComment());
    });

    /**
     * @returns {Boolean} true if the value <input> is not blank
     **/
    self.isComplete = ko.computed(function() {
        return !$osf.isBlank(self.value());
    });

    self.valid = ko.observable(null);

    self.init();
};
/**
 * Maps 'object' type Questions's properties to sub-Questions
 **/
Question.prototype.init = function() {
    var self = this;
    if (self.type === 'object') {
        $.each(self.properties, function(prop, field) {
            self.properties[prop] = new Question(field, prop);
        });
    }
};
/**
 * Creates a new comment from the current value of Question.nextComment and clears nextComment
 **/
Question.prototype.addComment = function() {
    var self = this;

    var comment = new Comment({
        value: self.nextComment()
    });
    self.nextComment('');
    self.comments.push(comment);
};
/**
 * Shows/hides the Question example
 **/
Question.prototype.toggleExample = function(){
    this.showExample(!this.showExample());
};

/**
 * Model for MetaSchema instances
 *
 * @param {Object} params: instantiation values
 * @param {String} params.schema_name
 * @param {Integer} params.schema_version
 * @param {String} params.title: display title of schema
 * @param {Schema} params.schema
 *
 * @type Schema
 * @property {String} title
 * @property {Integer} version
 * @property {String} description
 * @property {String[]} fulfills: array of requirements/goals that this schema fulfills
 * @property {Page[]} pages
 *
 * @type Page
 * @property {String} id
 * @property {String} title
 * @property {Question[]} questions
 **/
var MetaSchema = function(params) {
    var self = this;

    self.name = params.schema_name;
    self.version = params.schema_version;
    self.title = params.title || params.schema.title;
    self.schema = params.schema || {};
    self.id = [self.name, self.version].join('_');

    $.each(self.schema.pages, function(i, page) {
        var mapped = {};
        $.each(page.questions, function(qid, question) {
            mapped[qid]  = new Question(question, qid);
        });
        self.schema.pages[i].questions = mapped;
    });
};

/** 
 * @class Draft 
 * Model for DraftRegistrations
 * 
 * @param {Object} params
 * @param {String} params.pk: primary key of Draft
 * @param {Object} params.registration_schema: data to be passed to MetaSchema constructor
 * @param {Object} params.registration_metadata: saved Draft data
 * @param {User} params.initiator
 * @param {Date} params.initated
 * @param {Date} params.updated
 * @property {Float} completion: percent completion of schema
**/
var Draft = function(params, metaSchema) {
    var self = this;

    self.pk = params.pk;
    self.metaSchema = metaSchema || new MetaSchema(params.registration_schema);
    self.schema = ko.pureComputed(function() {
        return self.metaSchema.schema;
    });
    self.schemaName = self.metaSchema.name;
    self.schemaVersion = self.metaSchema.version;
    self.schemaData = params.registration_metadata || {};

    self.initiator = params.initiator;
    self.initiated = new Date(params.initiated);
    self.updated = new Date(params.updated);
    self.completion = ko.computed(function() {
        var total = 0;
        var complete = 0;        
        if (self.schemaData) {
            var schema = self.schema();
            $.each(schema.pages, function(i, page) {
                $.each(page.questions, function(qid, question) {
                    var q = self.schemaData[qid];                    
                    if(q && !$osf.isBlank(q.value)) {
                        complete++;
                    }
                    total++;
                });
            });
           return Math.ceil(100 * (complete / total));
        }
        return 0;
    });
};

/** 
 * @class RegistrationEditor
 * 
 * @param {Object} urls
 * @param {String} urls.update: endpoint to update a draft instance
 * @param {String} editorID: id of editor DOM node
 * @property {ko.observable[Boolean]} readonly
 * @property {ko.observable[Draft]} draft
 * @property {ko.observable[Question]} currentQuestion
 * @property {Object} extensions: mapping of extenstion names to their view models
 *
 * Notes:
 * - The editor can be extended by calling #extendEditor with a type and it's associated ViewModel. 
 *   When the context for that type's schema template is built (see #context), that type's ViewModel
 *   is instantiated with the current scope's data as an argument
 **/
var RegistrationEditor = function(urls, editorId) {

    var self = this;

    self.urls = urls;

    self.readonly = ko.observable(false);

    self.draft = ko.observable();

    self.currentQuestion = ko.observable();
    self.currentPages = ko.computed(function() {
        var draft = self.draft();
        if(!draft){
            return [];
        }
        var schema = draft.schema();
        if(!schema) {
            return [];
        }
        return schema.pages;
    });

    self.lastSaveTime = ko.computed(function() {        
        if(!self.draft()) {
            return null;
        }
        return self.draft().updated;
    });
    self.formattedDate = formattedDate;
    
    self.iterObject = $osf.iterObject;

    self.extensions = {};
};
/**
 * Load draft data into the editor
 *
 * @param {Draft} draft
 **/
RegistrationEditor.prototype.init = function(draft) {
    var self = this;

    self.draft(draft);
    var metaSchema = draft.metaSchema;

    var schemaData = {};
    if(draft) {
        schemaData = draft.schemaData || {};
    }

    var questions = self.flatQuestions();
    $.each(questions, function(i, question) {
        var val = schemaData[question.id];
        if(val) {
            if(question.type === 'object') {
                $.each(question.properties, function(prop, subQuestion) {
                    val = schemaData[question.id][prop];
                    if(val) {
                        subQuestion.value(val.value);
                        subQuestion.comments($.map(val.comments, function(data) {
                            return new Comment(data);
                        }));
                    }
                });
            }
            else {
                question.value(val.value);
                question.comments($.map(val.comments, function(data) {
                    return new Comment(data);
                }));
            }
        }
    });
    self.currentQuestion(questions.shift());
};
/**
 * @returns {Question[]} flat list of the current schema's questions
 **/
RegistrationEditor.prototype.flatQuestions = function() {
    var self = this;

    var flat = [];
    
    $.each(self.currentPages(), function(i, page) {
        $.each(page.questions, function(qid, question) {
            flat.push(question);
        });
    });
    return flat;
};
/**
 * Creates a template context for editor type subtemplates. Looks for the data type
 * in the extension map, and if found instantiates that type's ViewModel. Otherwise
 * return the bare data Object
 *
 * @param {Object} data: data in current editor template scope
 * @returns {Object|ViewModel}
 **/
RegistrationEditor.prototype.context = function(data) {
    if (this.extensions[data.type]) {
        return new this.extensions[data.type](data);
    }
    return data;
};
/**
 * Extend the editor's recognized types
 * 
 * @param {String} type: unique type
 * @param {Constructor} ViewModel
 **/
RegistrationEditor.prototype.extendEditor = function(type, ViewModel) {
    this.extensions[type] = ViewModel;
};
RegistrationEditor.prototype.lastSaved = function() {
    var self = this;

    var t = self.lastSaveTime();
    if (t) {
        return t.toGMTString();
    } else {
        return 'never';
    }
};
RegistrationEditor.prototype.nextPage = function() {
    var self = this;

    var currentQuestion = self.currentQuestion();

    var questions = self.flatQuestions();
    var index = $osf.indexOf(questions, function(q){
        return q.id === currentQuestion.id;
    });
    if(index + 1 === questions.length) {
        self.currentQuestion(questions.shift());
    }
    else {
        self.currentQuestion(questions[index + 1]);
    }
};
RegistrationEditor.prototype.previousPage = function() {
    var self = this;

    var currentQuestion = self.currentQuestion();

    var questions = self.flatQuestions();
    var index = $osf.indexOf(questions, function(q){
        return q.id === currentQuestion.id;
    });
    if(index - 1 < 0){
        self.currentQuestion(questions.pop());
    }
    else {
        self.currentQuestion(questions[index - 1]);
    }
};
RegistrationEditor.prototype.selectPage = function(page) {
    var self = this;

	var firstQuestion = page.questions[Object.keys(page.questions)[0]];
    self.currentQuestion(firstQuestion);
};
RegistrationEditor.prototype.updateData = function(response) {
    var self = this;

    var draft = self.draft();
    draft.pk = response.pk;
    draft.updated = new Date(response.updated);
    self.draft(draft);
};
RegistrationEditor.prototype.create = function(schemaData) {
    var self = this;

    var metaSchema = self.draft().metaSchema;

    return $osf.postJSON(self.urls.create, {
        schema_name: metaSchema.name,
        schema_version: metaSchema.version,
        schema_data: schemaData
    }).then(self.updateData.bind(self));
};
RegistrationEditor.prototype.submit = function() {
    var self = this;
    
    var currentNode = window.contextVars.node
    var currentUser = window.contextVars.currentUser
    var url = '/api/v1/project/' + currentNode.id +  '/draft/submit/' + currentUser.id + '/'
    
    bootbox.dialog({
	message: "Please verify that all required fields are filled out:<br><br>\
	    <strong>Required:</strong><br>\
	Title<br> COI<br> Authors<br> Research<br> Certify<br> Data<br> Rationale<br> Sample<br> Type<br> Randomized?<br> \
	Covariates<br> Design<br> Blind<br> Outcome<br> Predictor<br> Statistical Models<br> Multiple Hypostheses<br> \
	Outcome Variables<br> Predictors<br> Incomplete<br> Exclusion<br><br> \
	    <strong>Optional:</strong><br>\
		Script",
		title: "Continue to submit this registration for review",
		buttons: {
			success: {
				label: "Submit",
				className: "btn-success",
				callback: function() {
					$.ajax({
						method: "POST",
						url: url,
						data: {node: currentNode, uid: currentUser.id},
						success: function(response) {
							bootbox.alert("Registration submitted for review!", function(result) {
								window.location.href = '/' + currentNode.id + '/registrations/';
							});
						}
					})
				}
			}
		}
	});
};
RegistrationEditor.prototype.save = function() {
    var self = this;

    var metaSchema = self.draft().metaSchema;
    var schema = metaSchema.schema;
    var data = {};
    $.each(schema.pages, function(i, page) {
        $.each(page.questions, function(qid, question) {
            if(question.type === 'object'){
                var value = {};
                $.each(question.properties, function(prop, subQuestion) {
                    value[prop] = {
                        value: subQuestion.value(),
                        comments: ko.toJS(subQuestion.comments())
                    };
                });
                data[qid] = value;
            }
            else {
                data[qid] = {
                    value: question.value(),
                    comments: ko.toJS(question.comments())
                };
            }
        });
    });

    if (!self.draft().pk){
        return self.create(data);
    }

    return $osf.putJSON(self.urls.update.replace('{draft_pk}', self.draft().pk), {
        schema_name: metaSchema.name,
        schema_version: metaSchema.version,
        schema_data: data
    }).then(self.updateData.bind(self));
};

var RegistrationManager = function(node, draftsSelector, editorSelector, controls) {
    var self = this;

    self.node = node;
    self.draftsSelector = draftsSelector;
    self.editorSelector = editorSelector;
    self.controls = controls;

    self.urls = {
        list: node.urls.api + 'draft/',
	submit: node.urls.api + 'draft/submit/',
        get: node.urls.api + 'draft/{draft_pk}/',
        delete: node.urls.api + 'draft/{draft_pk}/',
        schemas: '/api/v1/project/schema/',
        edit: node.urls.web + 'draft/{draft_pk}/'
    };

    self.schemas = ko.observableArray();
    self.selectedSchema = ko.observable({
        description: ''
    });

    // TODO: convert existing registration UI to frontend impl.
    // self.registrations = ko.observable([]);
    self.drafts = ko.observableArray();

    self.loading = ko.observable(true);

    self.preview = ko.observable(false);

    // bound functions
    self.formattedDate = formattedDate;
    self.getDraftRegistrations = $.getJSON.bind(null, self.urls.list);
    self.getSchemas = $.getJSON.bind(null, self.urls.schemas);

    self.sortedDrafts = ko.computed(function() {
        return self.drafts().sort(function(a, b) {
            return a.initiated > b.initiated;
        });
    });

    self.previewSchema = ko.computed(function() {
        var schema = self.selectedSchema();
        return {
            schema: schema.schema,
            readonly: true
        };
    });

    self.controls.showManager();
};
RegistrationManager.prototype.init = function() {
    var self = this;

    $osf.applyBindings(self, self.draftsSelector);

    var getSchemas = self.getSchemas();

    getSchemas.then(function(response) {
        self.schemas(
            $.map(response.meta_schemas, function(schema) {
                return new MetaSchema(schema);
            })
        );
    });

    var getDraftRegistrations = self.getDraftRegistrations();

    getDraftRegistrations.then(function(response) {
        self.drafts(
            $.map(response.drafts, function(draft) {
                return new Draft(draft);
            })
        );
    });

    $.when(getSchemas, getDraftRegistrations).then(function() {
        self.loading(false);
    });
};
RegistrationManager.prototype.refresh = function() {
    var self = this;

    var getSchemas = self.getSchemas();

    getSchemas.then(function(response) {
        self.schemas(
            $.map(response.meta_schemas, function(schema) {
                return new MetaSchema(schema);
            })
        );
    });

    var getDraftRegistrations = self.getDraftRegistrations();

    getDraftRegistrations.then(function(response) {
        self.drafts(
            $.map(response.drafts, function(draft) {
                return new Draft(draft);
            })
        );
    });

    $.when(getSchemas, getDraftRegistrations).then(function() {
        self.loading(false);
    });
};
RegistrationManager.prototype.blankDraft = function(metaSchema) {
    return new Draft({}, metaSchema);
};
RegistrationManager.prototype.launchEditor = function(draft) {
    var self = this;
    var node = self.node;

    bootbox.hideAll();
    self.controls.showEditor();

    var newDraft;
    if (self.regEditor) {
        //self.regEditor.destroy();
        newDraft = self.regEditor.init(draft);
    }
    else {
        self.regEditor = new RegistrationEditor({
            schemas: '/api/v1/project/schema/',
            create: node.urls.api + 'draft/',
            update: node.urls.api + 'draft/{draft_pk}/',
            get: node.urls.api + 'draft/{draft_pk}/'
        }, 'registrationEditor');
        newDraft = self.regEditor.init(draft);
        $osf.applyBindings(self.regEditor, self.editorSelector);
    }
};
RegistrationManager.prototype.editDraft = function(draft) {
    window.location = this.urls.edit.replace('{draft_pk}', draft.pk);
};
RegistrationManager.prototype.deleteDraft = function(draft) {
    var self = this;

    bootbox.confirm('Are you sure you want to delete this draft registration?', function(confirmed) {
        if(confirmed) {
            $.ajax({
                url: self.urls.delete.replace('{draft_pk}', draft.pk),
                method: 'DELETE'
            }).then(function() {
                self.drafts.remove(function(item) {
                    return item.pk === draft.pk;
                });
            });
        }
    });
};
RegistrationManager.prototype.beforeCreateDraft = function() {
    var self = this;

    var node = self.node;

    self.selectedSchema(self.schemas()[0]);
    self.preview(true);
};
RegistrationManager.prototype.createDraft = function() {
    var self = this;

    var node = self.node;

    var schema = self.selectedSchema();
    $osf.postJSON(node.urls.web + 'draft/', {
        schema_name: schema.name,
        schema_version: schema.version
    });
};

module.exports = {
    Draft: Draft,
    RegistrationEditor: RegistrationEditor,
    RegistrationManager: RegistrationManager
};
