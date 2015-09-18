/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;
var $ = require('jquery');
var utils = require('tests/utils');
var faker = require('faker');

var bootbox = require('bootbox');

var $osf = require('js/osfHelpers');

window.contextVars.currentUser = {
    fullname: faker.name.findName(),
    id: 1
};
var registrationUtils = require('js/registrationUtils');

var utilities = registrationUtils.utilities;
var Comment = registrationUtils.Comment; // jshint ignore:line
var Question = registrationUtils.Question;
var MetaSchema = registrationUtils.MetaSchema;
var Draft = registrationUtils.Draft;
var RegistrationEditor = registrationUtils.RegistrationEditor;
var RegistrationManager = registrationUtils.RegistrationManager;

var mkMetaSchema = function() {
    var questions = {};
    var qid;
    [1, 1, 1].map(function() {
        qid = faker.internet.ip();
        questions[qid] = {
            type: 'string',
            format: 'text'
        };
    });

    var params = {
        schema_name: 'My Schema',
        schema_version: 1,
        title: 'A schema',
        schema: {
            title: 'A schema',
            version: 1,
            description: 'A very interesting schema',
            fulfills: [],
            pages: [1, 1, 1].map(function() {
                return {
                    id: faker.internet.ip(),
                    title: 'Page',
                    questions: questions
                };
            })
        },
        id: 'asdfg'
    };

    var ms = new MetaSchema(params);
    return [qid, params, ms];
};

describe('Comment', () => {
    describe('#constructor', () => {
        it('loads in optional instantiation data', () => {
            var user = {
                fullname: faker.name.findName(),
                id: 2
            };
            var data = {
                user: user,
                lastModified: faker.date.past(),
                value: faker.lorem.sentence()
            };
            var comment = new Comment(data);
            assert.equal(comment.user, user);
            assert.equal(comment.lastModified.toString(), new Date(data.lastModified).toString());
            assert.equal(comment.value(), data.value);
        });
        it('defaults user to the global currentUser', () => {
            var comment = new Comment();
            assert.deepEqual(comment.user, window.contextVars.currentUser);
        });
    });
    describe('#saved', () => {
        it('is true if the comment has data', () => {
            var comment = new Comment();
            assert.isFalse(comment.saved());

            var user = {
                fullname: faker.name.findName(),
                id: 2
            };
            var data = {
                user: user,
                lastModified: faker.date.past(),
                value: faker.lorem.sentence()
            };
            comment = new Comment(data);
            assert.isTrue(comment.saved());
        });
    });
    describe('#canDelete', () => {
        it('is true if the global currentUser is the same as comment.user', () => {
            var comment = new Comment();
            assert.isTrue(comment.canDelete());

            var user = {
                fullname: faker.name.findName(),
                id: 2
            };
            var data = {
                user: user,
                lastModified: faker.date.past(),
                value: faker.lorem.sentence()
            };
            comment = new Comment(data);
            assert.isFalse(comment.canDelete());
        });
    });
    describe('#viewComment', () => {
        it('adds a user id that is not the author to a the seenBy array', () => {
            var comment = new Comment();
            var currentUser = window.contextVars.currentUser;

            var user = {
                fullname: faker.name.findName(),
                id: 2
            };
            var data = {
                user: user,
                lastModified: faker.date.past(),
                value: faker.lorem.sentence()
            };
            comment.viewComment(user);
            assert.isTrue(comment.seenBy().length === 2);
            assert.isTrue(comment.seenBy().indexOf(user.id) !== -1);
            assert.isTrue(comment.seenBy().indexOf(currentUser.id) !== -1);

            comment = new Comment(data);
            comment.viewComment(currentUser);
            assert.isTrue(comment.seenBy().length === 2);
            assert.isTrue(comment.seenBy().indexOf(user.id) !== -1);
            assert.isTrue(comment.seenBy().indexOf(currentUser.id) !== -1);
        });
    });
    describe('#seenBy', () => {
        it('is a list of all user ids that have seen the comment', () => {
            var comment = new Comment();
            var currentUser = window.contextVars.currentUser;
            assert.isTrue(comment.seenBy().length === 1);
            assert.isTrue(comment.seenBy().indexOf(currentUser.id) !== -1);

            var user = {
                fullname: faker.name.findName(),
                id: 2
            };
            var data = {
                user: user,
                lastModified: faker.date.past(),
                value: faker.lorem.sentence()
            };
            comment = new Comment(data);
            assert.isTrue(comment.seenBy().length === 1);
            assert.isTrue(comment.seenBy().indexOf(user.id) !== -1);

            comment.viewComment(currentUser);
            assert.isTrue(comment.seenBy().length === 2);
            assert.isTrue(comment.seenBy().indexOf(currentUser.id) !== -1);

        });
    });
    describe('#canEdit', () => {
        it('is true if the comment is saved and the current user is the comment creator', () => {
            var comment = new Comment();
            assert.isFalse(comment.canEdit());
            comment.saved(true);
            assert.isTrue(comment.canEdit());

            var user = {
                fullname: faker.name.findName(),
                id: 2
            };
            var data = {
                user: user,
                lastModified: faker.date.past(),
                value: faker.lorem.sentence()
            };
            comment = new Comment(data);
            assert.isFalse(comment.canEdit());
            comment.saved(true);
            assert.isFalse(comment.canEdit());
        });
    });
    describe('#isDeleted', () => {
        it('is true when a comment is deleted and sets the value to a deleted message', () => {
            var comment = new Comment();
            assert.isFalse(comment.isDeleted());
            comment.isDeleted(true);
            assert.isTrue(comment.isDeleted());
            assert.equal(comment.value(), '');

            var user = {
                fullname: faker.name.findName(),
                id: 2
            };
            var data = {
                user: user,
                lastModified: faker.date.past(),
                value: faker.lorem.sentence()
            };
            comment = new Comment(data);
            assert.isFalse(comment.isDeleted());
            comment.isDeleted(true);
            assert.isTrue(comment.isDeleted());
            assert.equal(comment.value(), '');
        });
    });
    describe('#author', () => {
        it('is always the user who creates the comment\'s fullname', () => {
            var comment = new Comment();
            assert.isTrue(comment.author() === window.contextVars.currentUser.fullname);

            var user = {
                fullname: faker.name.findName(),
                id: 2
            };
            var data = {
                user: user,
                lastModified: faker.date.past(),
                value: faker.lorem.sentence()
            };
            comment = new Comment(data);
            assert.isFalse(comment.author() === window.contextVars.currentUser.fullname);
            assert.isTrue(comment.author() === user.fullname);
        });
    });
    describe('#getAuthor', () => {
        it('returns You if the current user is the commenter else the commenter name', () => {
            var comment = new Comment();
            assert.isTrue(comment.getAuthor() === 'You');

            var user = {
                fullname: faker.name.findName(),
                id: 2
            };
            var data = {
                user: user,
                lastModified: faker.date.past(),
                value: faker.lorem.sentence()
            };
            comment = new Comment(data);
            assert.isTrue(comment.getAuthor() === user.fullname);
        });
    });
});

describe('Question', () => {
    var id, question, q;
    beforeEach(() => {
        id = faker.internet.ip();
        question = {
            title: faker.internet.domainWord(),
            nav: faker.internet.domainWord(),
            type: 'string',
            format: 'text',
            description: faker.lorem.sentence(),
            help: faker.lorem.sentence(),
            required: true,
            options: [1, 1, 1].map(faker.internet.domainWord)
        };
        q = new Question(question, id);
    });

    describe('#constructor', () => {
        it('loads in optional instantiation data', () => {
            assert.equal(q.id, id);
            assert.equal(q.title, question.title);
            assert.equal(q.nav, question.nav);
            assert.equal(q.type, question.type);
            assert.equal(q.format, question.format);
            assert.equal(q.description, question.description);
            assert.equal(q.help, question.help);
            assert.equal(q.required, question.required);
            assert.equal(q.options, question.options);
            assert.isDefined(q.value);
        });
    });
    describe('#allowAddNext', () => {
        it('is true if the Question\'s nextComment is not blank', () => {
            assert.isFalse(q.allowAddNext());
            q.nextComment('not blank');
            assert.isTrue(q.allowAddNext());
        });
    });
    describe('#isComplete', () => {
        it('is true if the Question\'s value is not blank', () => {
            assert.isFalse(q.isComplete());
            q.value('not blank');
            assert.isTrue(q.isComplete());
        });
    });
    describe('#isValid', () => {
        it('is true if the Question\'s value is not empty and the question is required', () => {
            assert.isFalse(q.value.isValid());
            q.value('not empty');
            assert.isTrue(q.value.isValid());
        });
    });
    describe('#init', () => {
        it('maps object-type Question\'s properties property to sub-Questions', () => {
            var props = {
                foo: {
                    type: 'number'
                }
            };

            var objType = new Question({
                type: 'object',
                properties: props
            });
            var obj = new Question(objType);
            assert.equal(obj.properties.foo.id, 'foo');
            assert.isDefined(obj.properties.foo.value);
        });
    });
    describe('#addComment', () => {
        it('creates a new Comment using the value of Question.nextComment, and clears Question.nextComment', () => {
            assert.equal(q.comments().length, 0);
            q.nextComment('A good comment');
            q.addComment();
            assert.equal(q.comments().length, 1);
            assert.equal(q.nextComment(), '');
        });
    });
    describe('#toggleExample', () => {
        it('toggles the value of Question.showExample', () => {
            assert.isFalse(q.showExample());
            q.toggleExample();
            assert.isTrue(q.showExample());
        });
    });
});

describe('MetaSchema', () => {
    describe('#constructor', () => {
        it('loads optional instantion data and maps question data to Question instances', () => {

            var ctx = mkMetaSchema();
            var qid = ctx[0];
            var params = ctx[1];
            var ms = ctx[2];
            assert.equal(ms.name, params.schema_name);
            assert.equal(ms.version, params.schema_version);
            assert.equal(ms.schema.pages[0].id, params.schema.pages[0].id);

            assert.isDefined(ms.schema.pages[2].questions[qid].value);
        });
    });
    describe('#flatQuestions', () => {
        it('creates a flat array of the schema questions', () => {
            var ctx = mkMetaSchema();
            var qid = ctx[0];
            var params = ctx[1];
            var ms = ctx[2];

            var questions = [];
            $.each(params.schema.pages, function(i, page) {
                $.each(page.questions, function(qid, question) {
                    questions.push(question);
                });
            });
            assert.deepEqual(questions, ms.flatQuestions());
        });
    });
});

describe('Draft', () => {
    var ms = mkMetaSchema()[2];
    
    var beforeRegisterUrl = faker.internet.ip();
    var registerUrl = faker.internet.ip();
    var params = {
        pk: faker.random.number(),
        registration_metadata: {},
        initiator: {
            name: faker.name.findName(),
            id: faker.internet.ip()
        },
        initiated: faker.date.past(),
        updated: faker.date.past(),
        urls: {
            before_register: beforeRegisterUrl,
            register: registerUrl
        }
    };

    var draft = new Draft(
        params, ms
    );

    describe('#constructor', () => {
        it('loads optional instantiation data and metaSchema instance', () => {
            assert.equal(draft.metaSchema.name, ms.name);
            assert.equal(draft.initiator.id, params.initiator.id);
            assert.equal(draft.updated.toString(), params.updated.toString());
        });
        it('calculates a percent completion based on the passed registration_metadata', () => {
            var ms = mkMetaSchema()[2];

            var data = {};
            var questions = ms.flatQuestions();
            $.each(questions, function(i, q) {
                data[q.id] = {
                    value: 'value'
                };
            });

            var params = {
                pk: faker.random.number(),
                registration_metadata: data,
                initiator: {
                    name: faker.name.findName(),
                    id: faker.internet.ip()
                },
                initiated: faker.date.past(),
                updated: faker.date.past()
            };

            var draft = new Draft(params, ms);

            assert.equal(draft.completion(), 100);
        });
    });
    describe('#beforeRegister', () => {
        var endpoints = [{
            method: 'GET',
            url: beforeRegisterUrl,
            response: {
                errors: ['Error'],
                prompts: ['Prompt']
            }
        }];
        var server;
        var getJSONSpy;
        var preRegisterErrorsStub;
        var preRegisterPromptsStub;
        var registerStub;
        before(() => {            
            server = utils.createServer(sinon, endpoints);
            getJSONSpy = sinon.spy($, 'getJSON');
            preRegisterErrorsStub = sinon.stub(draft, 'preRegisterErrors');
            preRegisterPromptsStub = sinon.stub(draft, 'preRegisterPrompts');
            registerStub = sinon.stub(draft, 'register');
        });
        after(() => {
            server.restore();
            $.getJSON.restore();
            draft.preRegisterErrors.restore();
            draft.preRegisterPrompts.restore();
            draft.register.restore();
        });
        afterEach(() => {
            preRegisterErrorsStub.reset();
            preRegisterPromptsStub.reset();
            registerStub.reset();
        });
        it('fetches pre-register messages', (done) => {
            draft.beforeRegister().always(function() {
                assert.isTrue(getJSONSpy.calledOnce);
                done();
            });
        });
        it('calls Draft#preRegisterErrors if there are errors', (done) => {
            draft.beforeRegister().always(function() {
                assert.isTrue(preRegisterErrorsStub.calledOnce);
                done();
            });            
        });
        it('calls Draft#preRegisterPrompts if there are prompts and no errors', (done) => {
            server.respondWith(
                beforeRegisterUrl, 
                function (xhr, id) {
                    xhr.respond(200, 
                                {'Content-Type': 'application/json'}, 
                                JSON.stringify({
                                    prompts: ['Warn']
                                }));
                });
            draft.beforeRegister().always(function() {
                assert.isTrue(preRegisterPromptsStub.calledOnce);
                done();
            });           
        });
        it('calls Draft#register if there are no errors and no prompts', (done) => {
            server.respondWith(
                beforeRegisterUrl, 
                '{}'
            );
            draft.beforeRegister().always(function() {
                assert.isTrue(registerStub.calledOnce);
                done();
            });            
        });        
    });
    describe('#register', () => {
        var server;
        var postJSONStub;
        before(() => {
            server = utils.createServer(sinon, []);
            postJSONStub = sinon.stub($osf, 'postJSON', function() {
                return $.Deferred();
            });
        });
        after(() => {
            server.restore();
            $osf.postJSON.restore();
        });
        it('POSTS the data passed into beforeRegister, and redirects on a success response', (done) => {
            server.respondWith(
                beforeRegisterUrl, 
                '{}'
            );
            var data = {some: 'data'};
            draft.beforeRegister(data).always(() => {                
                assert.isTrue(
                    postJSONStub.calledOnce && 
                    postJSONStub.calledWith(
                        registerUrl,
                        data
                    )
                );
                done();
            });            
        });
    });
});

describe('RegistrationEditor', () => {
    var ms = mkMetaSchema()[2];
    var questions = ms.flatQuestions();

    var metaData = {};
    $.each(questions, function(i, q) {
        metaData[q.id] = {
            value: faker.company.bsNoun()
        };
    });
            
    var beforeRegisterUrl = faker.internet.ip();
    var registerUrl = faker.internet.ip();
    var params = {
        pk: faker.random.number(),
        registration_metadata: metaData,
        initiator: {
            name: faker.name.findName(),
            id: faker.internet.ip()
        },
        initiated: faker.date.past(),
        updated: faker.date.past(),
        urls: {
            before_register: beforeRegisterUrl,
            register: registerUrl
        }
    };

    var draft = new Draft(
        params, ms
    );

    var editor;
    var createUrl = faker.internet.ip();
    var updateUrl = faker.internet.ip() + '/{draft_pk}/';
    before(() => {
        editor = new RegistrationEditor({
            create: createUrl,
            update: updateUrl
        }, '#id');
        editor.init(draft);
    });
    describe('#init', () => {
        it('loads draft data', () => {
            assert.equal(editor.draft(), draft);
        });
        it('#loads schema data into the schema', () => {
            $.each(questions, function(i, q) {
                assert.equal(q.value(), metaData[q.id].value);
            });
        });
    });
    describe('#create', () => {        
        var postJSONStub;
        var updateDataStub;
        before(() => {
            postJSONStub = sinon.stub($osf, 'postJSON', function() {
                var ret = $.Deferred();
                ret.resolve();
                return ret;                
            });
            updateDataStub = sinon.stub(editor, 'updateData');
        });
        after(() => {
            $osf.postJSON.restore();
            editor.updateData.restore();
        });
        it('POSTs to the create URL with the current draft state', (done) => {
            editor.create({}).always(function() {
                var metaSchema = draft.metaSchema;
                assert.isTrue(
                    postJSONStub.calledWith(
                        createUrl,
                        {
                            schema_name: metaSchema.name,
                            schema_version: metaSchema.version,
                            schema_data: {}
                        }
                    )
                );
                done();
            });            
        });
    });
    describe('#save', () => {
        var putSaveDataStub;
        var updateDataStub;
        beforeEach(() => {
            putSaveDataStub = sinon.stub(editor, 'putSaveData', function() {
                var ret = $.Deferred();
                ret.resolve();
                return ret;
            });
            updateDataStub = sinon.stub(editor, 'updateData');
        });
        afterEach(() => {
            editor.putSaveData.restore();
            editor.updateData.restore();
        });
        it('PUTs to the update URL with the current draft state', () => {
            var metaSchema = draft.metaSchema;
            questions[0].value('Updated');
            editor.save();
            
            var data = {};
            $.each(questions, function(i, q) {
                data[q.id] = {
                    value: q.value()
                };
            });
            
            assert.isTrue(
                putSaveDataStub.calledWith(
                    {
                        schema_name: metaSchema.name,
                        schema_version: metaSchema.version,
                        schema_data: data
                    }
                )
            );
        });
    });
});
