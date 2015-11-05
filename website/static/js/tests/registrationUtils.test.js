/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;
var $ = require('jquery');
var utils = require('tests/utils');
var faker = require('faker');

var bootbox = require('bootbox');

var $osf = require('js/osfHelpers');
var utils = require('./utils');

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
    var questions = [];
    var qid;
    for ( var i = 0; i < 3; i++ ) {
        qid = 'q' + i;
        questions.push({
            qid: qid,
            type: 'string',
            format: 'text'
        });
    }

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

            assert.isDefined(ms.schema.pages[2].questions.q0.value);
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
        before(() => {
            postJSONStub = sinon.stub($osf, 'postJSON', function() {
                var ret = $.Deferred();
                ret.resolve({pk : '12345'});
                return ret;
            });
        });
        after(() => {
            postJSONStub.restore();
        });
        it('POSTs to the create URL with the current draft state', (done) => {

            editor.create({}).always(function() {
                assert.deepEqual(
                    postJSONStub.args[0][1].schema_data,
                    {}
                );
                done();
            });
        });
    });
    describe('#save', () => {
        var putSaveDataStub;
        var onSaveSucces;
        beforeEach(() => {
            putSaveDataStub = sinon.stub(editor, 'putSaveData', function() {
                var ret = $.Deferred();
                ret.resolve({pk: '12345'}, 1, {});
                return ret.promise();
            });
            sinon.stub(editor, 'onSaveSucces');
        });
        afterEach(() => {
            editor.putSaveData.restore();
            editor.onSaveSucces.restore();
        });
        it('PUTs to the update URL with the current draft state', () => {
            var metaSchema = draft.metaSchema;
            questions[0].value('Updated');
            editor.save();

            var data = {};
            $.each(questions, function(i, q) {
                data[q.id] = {
                    value: q.value()
                    // comments: []
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
