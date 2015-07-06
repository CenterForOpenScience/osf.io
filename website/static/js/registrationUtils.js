var $ = require('jquery');
var ko = require('knockout');
var bootbox = require('bootbox');
var moment = require('moment');

var $osf = require('js/osfHelpers');
var oop = require('js/oop');

require('js/registrationEditorExtensions');

var iterObject = function(obj) {
    var ret = [];
    $.each(obj, function(prop, value) {
        ret.push({
            key: prop,
            value: value
        });
    });
    return ret;
};

function isBlank(item) {    
    return !item || /^\s*$/.test(item || '');
}

function indexOf(array, searchFn) {
    var len = array.length;
    for(var i = 0; i < len; i++) {
        if(searchFn(array[i])) {
            return i;
        }
    }
    return -1;
}

var formattedDate = function(dateString) {
    if (!dateString) {
        return 'never';
    }
    var d = new Date(dateString);
    return moment(dateString).fromNow() + ' (' + d.toGMTString() + ')';
};

//######### Commentable ###########
var currentUser = window.contextVars.currentUser || {
    id: null,
    name: 'Anonymous'
};

var Comment = function(data) {
    var self = this;
    
    self.saved = ko.observable(data ? true : false);   

    data = data || {};
    self.user = data.user || currentUser;
    self.lastModified = moment(data.lastModified || new Date());
    self.value = ko.observable(data.value || '');

    self.author = ko.pureComputed(function() {
        if (self.user.id === currentUser.id) {
            return 'You';
        }
        else {
            return self.user.name;
        }
    });

    self.canDelete = ko.pureComputed(function() {
        return self.user.id === currentUser.id;
    });
    self.canEdit = ko.pureComputed(function() {
        return self.saved() && self.user.id === currentUser.id;
    });
};

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

////////////////////

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

    self.showExample = ko.observable(false);    
    
    self.comments = ko.observableArray(
        $.map(data.comments || [], function(comment) {
            return new Comment(comment);
        })
    );
    self.nextComment = ko.observable('');
    self.allowAddNext = ko.computed(function() {
        return !isBlank(self.nextComment());
    });

    self.isComplete = ko.computed(function() {
        return !isBlank(self.value());
    });
    
    self.init();
};
Question.prototype.init = function() {
    var self = this;
    if (self.type === 'object') {
        $.each(self.properties, function(prop, field) {
            self.properties[prop] = new Question(field, prop);
        });
    }
};
Question.prototype.addComment = function() {
    var self = this;

    var comment = new Comment({
        value: self.nextComment()
    });
    self.nextComment('');
    self.comments.push(comment);
};
Question.prototype.toggleExample = function(){
    this.showExample(!this.showExample());
};
/////////////////////

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
    self.initiated = params.initiated;
    self.updated = params.updated;
    self.completion = 0.0;
    var total = 0;
    var complete = 0;
    if (self.schemaData) {
        for (var i = 0; i < self.metaSchema.schema.pages.length; i++) {
            var page = self.metaSchema.schema.pages[i];
            $.each(page.questions, function(qid, question) {
                if (self.schemaData[qid] && self.schemaData[qid].value) {
                    complete++;
                }
                total++;
            });
        }
        self.completion = 100 * (complete / total);
    }
};

var RegistrationEditor = function(urls, editorId, utils) {

    var self = this;
    self.utils = utils;

    self.urls = urls; 

    self.readonly = ko.observable(false);

    self.draftPk = ko.observable(false);

    self.draft = ko.observable();
    self.currentSchema = ko.computed(function() {
        var draft = self.draft();        
        if (!draft || !draft.schema()) {            
            return {pages: []};
        }
        else {
            return draft.schema();
        }
    });     

    self.currentQuestion = ko.observable();
    self.currentPages = ko.computed(function() {
        return self.currentSchema().pages;
    });
    
    self.lastSaveTime = ko.observable();
    self.formattedDate = formattedDate;

    self.flatQuestions = ko.computed(function() {
        var flat = [];
        var schema = self.currentSchema();
        
        $.each(schema.pages, function(i, page) {
            $.each(page.questions, function(qid, question) {
                flat.push(question);
            });
        });
        return flat;
    });

    self.iterObject = iterObject;

    self.extensions = {};
};
RegistrationEditor.prototype.init = function(draft) {
    var self = this;

    self.draft(draft);
    var metaSchema = draft.metaSchema;
    
    var schemaData = {};
    if(draft) {
        schemaData = draft.schemaData || {};
    }
    
    var keys = Object.keys(metaSchema.schema.pages[0].questions);
    self.currentQuestion(metaSchema.schema.pages[0].questions[keys.shift()]);

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
};
RegistrationEditor.prototype.context = function(data) {
    if (this.extensions[data.type]) {
        return new this.extensions[data.type](data);
    }
    return data;
};
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
    var index = indexOf(questions, function(q){
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
    var index = indexOf(questions, function(q){
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
    self.currentQuestion(page.questions[0]);
};
RegistrationEditor.prototype.updateData = function(response) {
    var self = this;

    self.draftPk(response.pk);    
    self.lastSaveTime(new Date());
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

    if (!self.draftPk()){
        return self.create(data);
    }

    return $osf.putJSON(self.urls.update.replace('{draft_pk}', self.draftPk()), {
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
        get: node.urls.api + 'draft/{draft_pk}/',
        delete: node.urls.api + 'draft/{draft_pk}/',
        schemas: '/api/v1/project/schema/'
    };

    self.schemas = ko.observableArray();
    self.selectedSchema = ko.observable();

    // TODO: convert existing registration UI to frontend impl.
    // self.registrations = ko.observable([]);
    self.drafts = ko.observableArray();
    /*
    self.drafts.subscribe(function(changes) {
        $.each(changes, function(i, change) {
            if(change.status === 'deleted' && self.regEditor) {
                self.regEditor.destroy();
            }
        });
    }, null, 'arrayChange');
     */

    self.loading = ko.observable(true);

    // bound functions
    self.formattedDate = formattedDate;
    self.getDraftRegistrations = $.getJSON.bind(null, self.urls.list);
    self.getSchemas = $.getJSON.bind(null, self.urls.schemas);

    self.sortedDrafts = ko.computed(function() {
        return self.drafts().sort(function(a, b) {
            return a.initiated > b.initiated;
        });
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
        }, 'registrationEditor', {
            addDraft: function(draft) {
                if (!self.drafts().filter(function(d) {
                    return draft.pk === d.pk;
                }).length) {
                    self.drafts.unshift(draft);
                }
            },
            updateDraft: function(draft) {
                self.drafts.remove(function(d) {
                    return d.pk === draft.pk;
                });
                self.drafts.unshift(draft);
            }
        });
        newDraft = self.regEditor.init(draft);    
        $osf.applyBindings(self.regEditor, self.editorSelector);
    }
};
RegistrationManager.prototype.editDraft = function(draft) {
    this.launchEditor(draft, draft.schema);
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
RegistrationManager.prototype.beforeRegister = function() {
    var self = this;

    var node = self.node;
   
    var VM = {
        title: node.title,
        parentTitle: node.parentTitle,
        parentUrl: node.parentRegisterUrl,
        category: node.category === 'project' ? node.category : 'component',
        schemas: self.schemas,
        selectedSchema: self.selectedSchema,
        cancel: bootbox.hideAll,
        launchEditor: self.launchEditor.bind(self),
        blankDraft: self.blankDraft.bind(self)
    };
    bootbox.dialog({
        title: 'Register ' + node.title,
        message: function() {
            var preRegisterMessage = ko.renderTemplate('preRegisterMessageTemplate', VM, {}, this);
        }
    });
};

module.exports = {
    RegistrationEditor: RegistrationEditor,
    RegistrationManager: RegistrationManager
};
