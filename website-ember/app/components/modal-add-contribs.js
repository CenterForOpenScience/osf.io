import Ember from 'ember';
import DS from 'ember-data';

import deferredPromise from '../utils/deferred-promise';
import permissions, {permissionSelector} from 'ember-osf/const/permissions';

/**
 * Wraps user data with additional properties to track whether a given user is a contributor on this project
 * @class OneContributor
 */
let OneContributor = Ember.ObjectProxy.extend({
    isContributor: false,
    selectedPermissions: permissions.WRITE
});

/**
 * Modal that handles adding and removing contributors from a project
 *
 * Sample usage:
 * ```handlebars
 * {{modal-add-contribs
 *   isOpen=showModal
 *   node=model
 *   contributors=contributors}}
 * ```
 * @class modal-add-contribs
 */
export default Ember.Component.extend({
    store: Ember.inject.service('store'),

    /**
     * @property {String} page Which page of the modal to display
     * @default whom|which|invite
     */
    page: 'whom',  // TODO: Replace this with components; temp feature

    // Permissions labels for dropdown (eg in modals)
    permissionOptions: permissionSelector,

    _wrapUserAsContributor(user, extra) {
        // Wrap a user instance to provide additional fields describing contributor status
        let options = { content: user };
        options = Ember.merge(options, extra);
        return OneContributor.create(options)
    },

    //////////////////////////////////
    //  OPTIONS FOR THE WHOM PAGE   //
    //////////////////////////////////
    // The username to search for
    _searchText: null,
    // Store results array from search. TODO: Make this store a promise so we can check fulfilled status
    searchResults: null,

    // People selected to add as contributors
    contribsToAdd: Ember.A(),
    contribsNotYetAdded: Ember.computed('searchResults', 'contribsToAdd.[]', function(item) {
        // TODO: Implement: searchResults not yet in contribsToAdd.
        // Use this for rendering the row widget.
        // Search results are users; contribsToAdd are users also.
        let selected = this.get('contribsToAdd');
        let searchResults = this.get('searchResults');
        return searchResults.filter((item) => !selected.contains(item));
    }),
    displayContribNamesToAdd: Ember.computed('contribsToAdd', function() {
        // TODO: Implement: join all names in list as string.
        // Was: addingSummary
    }),

    // Some computed properties
    canViewParent: Ember.computed.alias('node.parent'), // TODO : verify first whether user can view parent. May need a new model field.

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
            let text = this.get('_searchText');
            if (!text) {
                return;
            }

            // TODO: Query from search.js is generic; can we simplify for this page?
            let simplestQuery = {
                query: {
                    filtered: {
                        query: {
                            query_string: {
                                default_field: '_all',
                                fields: ['_all', 'job^1', 'school^1', 'all_jobs^0.125', 'all_schools^0.125'],
                                query: text,
                                analyze_wildcard: true,
                                lenient: true
                            }
                        }
                    }
                },
                from: 0,  // TODO: Make configurable for pagination
                size: 10  // TODO: Make configurable for pagination
            };
            // TODO: add payload fields for 'from' and 'size' to control response?
            let resp = Ember.$.ajax({
                method: 'POST',
                url: '/api/v1/search/user/',
                contentType: 'application/json',
                data: JSON.stringify(simplestQuery)
            });
            let promiseResp = deferredPromise(resp);
            promiseResp.then((res) => {
                let ids = res.results.map((item) => item.id);
                // As long as # records < # api results pagesize, this will be fine wrt pagination. (TODO: specify parameter to be safe)
                if (ids.length) {
                    return this.get('store').query('user', { 'filter[id]': ids.join(',') });
                } else {
                    return Ember.A();  // TODO: Do something with this result
                }
            }).then((res) => {
                // Annotate each user search result based on whether they are a project contributor
                let contributorIds = this.get('contributors').map((item) => item.get('userId'));
                return res.map((item) => this._wrapUserAsContributor(item,
                    { isContributor: contributorIds.contains(item.id) }
                ));
            }).then((res) => this.set('searchResults', res)
            ).catch((error) => console.log('Query failed with error', error));  // TODO: Show errors to user
        },
        importContribsFromParent() {
            //TODO: Import contributors from parent
            console.log('Imported contributors!');
        },

        addAllContributors() {
            // TODO: Implement, was addAll in contribAdder.js
            // TODO: Filter out users who are already on the project
            let users = this.get('searchResults');
            this.get('contribsToAdd').addObjects(users);
        },
        addOneContributor(user) {
            // Add the specified search result to the list of users who will be added to the project (pending additional options)
            // TODO: Implement. Was $root.add
            this.get('contribsToAdd').addObject(user);
        },
        removeAllContributors() {
            // TODO: Implement. Deselects contributors. Was removeAll in contribAdder.js
            // TODO: Make sure this doesn't remove users who are already on the project
            this.get('contribsToAdd').clear();
        },
        removeOneContributor(user) {
            // TODO: Implement.  Was $root.remove.
            // Remove the specified search result from the list of users who will be added to the project (pending additional options)
            this.get('contribsToAdd').removeObject(user);
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
