/* jshint node: true */
// jscs:disable disallowEmptyBlocks

module.exports = function(environment) {
    var ENV = {
        modulePrefix: 'website-ember',
        environment: environment,
        baseURL: '/',
        locationType: 'auto',

        authorizationType: 'cookie',
        'ember-simple-auth': {
            authorizer: 'authorizer:osf-cookie',
            authenticator: 'authenticator:osf-cookie'
        },
        i18n: {
            defaultLocale: 'en-US'
        },

        EmberENV: {
            FEATURES: {
                // Here you can enable experimental features on an ember canary build
                // e.g. 'with-controller': true
            },
            EXTEND_PROTOTYPES: {
                Date: false,
            }
        },

        APP: {
            // Here you can pass flags/options to your application instance
            // when it is created
        }
    };

    if (environment === 'development') {
        // ENV.APP.LOG_RESOLVER = true;
        // ENV.APP.LOG_ACTIVE_GENERATION = true;
        // ENV.APP.LOG_TRANSITIONS = true;
        // ENV.APP.LOG_TRANSITIONS_INTERNAL = true;
        // ENV.APP.LOG_VIEW_LOOKUPS = true;
    }

    if (environment === 'test') {
        // Testem prefers this...
        ENV.baseURL = '/';
        ENV.locationType = 'none';

        // keep test console output quieter
        ENV.APP.LOG_ACTIVE_GENERATION = false;
        ENV.APP.LOG_VIEW_LOOKUPS = false;

        ENV.APP.rootElement = '#ember-testing';
    }

    if (environment === 'production') {
        // Add production settings here
    }

    return ENV;
};
