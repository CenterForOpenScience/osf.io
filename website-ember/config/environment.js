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
            }
        },

        APP: {
            // Here you can pass flags/options to your application instance
            // when it is created
            featureFlags: {
                // Feature flags: things not ready to release, or parts of UI that depend on unreleased APIv2 functionality
                unregisteredContributors: true, // Blocked by OSF-6761. Must work with cookies.
                educationSchools: true, // Blocked by OSF-6769, serializer must provide data
                collaborationCount: true, // # projects in common to display in search results: No specific ticket or commitment to implement
                paginationWidget: false, // Blocked by EOSF-135, Widget to paginate multiple existing or new results
                viewOnlyLinks: false, // Blocked by EOSF-112
                treeWidgetAvailable: true, // Blocked by EOSF-134. Depends on hierarchical treebeard-like widget; no ticket available
            }
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
