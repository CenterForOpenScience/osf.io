import Ember from 'ember';

import deferredPromise from '../utils/deferred-promise';

/**
 * Modal that handles adding and removing contributors from a project
 * @class modal-add-contribs
 */
export default Ember.Component.extend({
    store: Ember.inject.service('store'),

    /**
     * @property {String} page Which page of the modal to display
     * @default whom|which|invite
     */
    page: 'whom',  // TODO: Replace this with components; temp feature

    //////////////////////////////////
    //  OPTIONS FOR THE WHOM PAGE   //
    //////////////////////////////////
    // The username to search for
    _searchText: null,
    // Store results array from search. TODO: Make this store a promise so we can check fulfilled status
    searchResults: null,

    // People selected to add as contributors
    contribsToAdd: Ember.A(),
    contribsNotYetAdded: Ember.computed('searchResults', 'contribsToAdd', function() {
        // TODO: Implement: searchResults not yet in contribsToAdd.
        // Use this for rendering the row widget.

    }),
    displayContribNamesToAdd: Ember.computed('contribsToAdd', function() {
        // TODO: Implement: join all names in list as string.
        // Was: addingSummary
    }),

    // Some computed properties
    canViewParent: Ember.computed.alias('model.parent'), // TODO : verify first whether user can view parent. May need a new model field.

    // TODO: This link should be hidden if the only search results returned are for people who are already contributors on the node
    // Was: addAllVisible, contribAdder.js
    showAddAll: true, // TODO: Implement

    actions: {
        selectPage(pageName) {
            console.log('Resetting component to page: ', pageName);
            this.set('page', pageName);
        },

        //////////////////////////////////
        //  Actions for the whom page   //
        //////////////////////////////////
        searchPeople() {
            // TODO: implement
            console.log('Performed a search');
            let text = this.get('_searchText');
            if (!text) {
                return;
            }

            // TODO: Query from search.js is generic; can we simplify for this page?
            let simplestQuery = {
                "query": {
                    "filtered": {
                        "query": {
                            "query_string": {
                                "default_field": "_all",
                                "fields": ["_all", "job^1", "school^1", "all_jobs^0.125", "all_schools^0.125"],
                                "query": text,
                                "analyze_wildcard": true,
                                "lenient": true
                            }
                        }
                    }
                },
                "from": 0,  // TODO: Make configurable for pagination
                "size": 10  // TODO: Make configurable for pagination
            };
            // TODO: add payload fields for "from" and "size" to control response?
            let resp = Ember.$.ajax({
                method: 'POST',
                url: '/api/v1/search/user/',
                contentType: 'application/json',
                data: JSON.stringify(simplestQuery)
            });
            resp = deferredPromise(resp);
            resp.then((res) => {
                let ids = res.results.map((item) => item.id);
                // As long as # records < # api results pagesize, this will be fine wrt pagination. (TODO: specify parameter to be safe)
                if (ids) {
                    return this.get('store').query('user', {'filter[id]': ids.join(',')});
                } else {
                    return [];  // TODO: Do something with this result
                }}).catch(() => console.log('Query failed with error'));  // TODO: Show errors to user
        },
        importContribsFromParent() {
            //TODO: Import contributors from parent
            console.log('Imported contributors!');
        },

        addAllContributors() {
            // TODO: Implement, was addAll in contribAdder.js
            console.log('Added all available results as contributors');
        },
        addOneContributor() {
            // TODO: Implement. Was $root.add
        },
        submitContributors() {
            console.log('Submitted contributors');
            // TODO: Implement. Send contribs list to server.

        },
        submitInvite() {
            // TODO: Not currently implemented pending required APIv2 capabilities
            console.log('User invited!');
        }
    }
});
