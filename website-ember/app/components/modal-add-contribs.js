import Ember from 'ember';

import deferredPromise from '../utils/deferred-promise';
import permissions, { permissionSelector } from 'ember-osf/const/permissions';

/**
 * Wraps user data with additional properties to track whether a given user is a contributor on this project
 * @class UserContributor
 */
let UserContributor = Ember.ObjectProxy.extend({
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
 *   contributors=contributors
 *   addContributor=closureAction}}
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
        return UserContributor.create(options);
    },

    /**
     * Given a list of user IDs, fetch the related user objects in a single query
     * @param {String[]} ids List of user IDs to fetch
     * @param options Additional options for the query
     * @private
     */
    _getUsersFromIds(ids, options) {
        let queryParams = { 'filter[id]': ids.join(',') };
        Ember.merge(queryParams, options);
        // TODO: Add verification that we aren't requesting more users than fit on a page of results
        if (ids.length) {
            return this.get('store').query('user', queryParams);
        } else {
            return Ember.A();  // TODO: Does this need to return a promise resolving to value?
        }
    },

    //////////////////////////////////
    //  OPTIONS FOR THE WHOM PAGE   //
    //////////////////////////////////
    // The username to search for
    _searchText: null,
    // Store results array from search.
    usersFound: null,
    isLoading: false, // Track loading state of search

    // Filtering functionality
    contribsToAdd: Ember.A(),
    contribsNotYetAdded: Ember.computed('usersFound', 'contribsToAdd.[]', function() {
        let contribsToAdd = this.get('contribsToAdd');
        let usersFound = this.get('usersFound');
        return usersFound.filter((item) => !contribsToAdd.contains(item));
    }),

    // Some computed properties
    canViewParent: Ember.computed.alias('node.parent'), // TODO : Deal with edge case where node has parent that user can't see

    // TODO: This link should be hidden if the only search results returned are for people who are already contributors on the node
    // Was: addAllVisible, contribAdder.js
    showAddAll: Ember.computed('usersFound', 'contribsNotYetAdded', function() {
        let usersFound = this.get('usersFound');
        if (!usersFound || !usersFound.length) {
            return false;
        }
        // Do not show the add all button if all the search results are already contributors.
        let filtered = this.get('contribsNotYetAdded').filterBy('isContributor', false);
        return !!filtered.length;
    }),

    //////////////////////////////////
    // OPTIONS FOR THE WHICH PAGE   //
    //////////////////////////////////
    displayContribNamesToAdd: Ember.computed('contribsToAdd', function() {
        // TODO: Implement: join all names in list as string to display who will be added to child projects.
        // Was: addingSummary
        return '';
    }),

    actions: {
        selectPage(pageName) {
            console.log('Resetting component to page: ', pageName);
            this.set('page', pageName);
        },

        //////////////////////////////////
        //  Actions for the whom page   //
        //////////////////////////////////
        searchPeople() {
            // TODO: Move to a separate file and fill in full generic query from search.js
            let text = this.get('_searchText');
            if (!text) {
                return;
            }

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
            this.set('isLoading', true);

            let resp = Ember.$.ajax({
                method: 'POST',
                url: '/api/v1/search/user/',
                contentType: 'application/json',
                data: JSON.stringify(simplestQuery)
            });
            let promiseResp = deferredPromise(resp);
            promiseResp.then((res) => {
                // Convert search results (JSON) to APIv2 user records with more info
                let userIdList = res.results.map((item) => item.id);
                // As long as # records < # api results pagesize, this will be fine wrt pagination. (TODO: specify parameter to be safe)
                return this._getUsersFromIds(userIdList);
            }).then((res) => {
                // Annotate each user search result based on whether they are a known project contributor
                let contributorIds = this.get('contributors').map((item) => item.get('userId'));
                return res.map((item) => this._wrapUserAsContributor(item,
                    { isContributor: contributorIds.contains(item.id) }
                ));
            }).then((res) => {
                this.set('usersFound', res);
                this.set('isLoading', false);
            }).catch((error) => {
                this.set('isLoading', false);
                console.log('Query failed with error', error);
            });  // TODO: Show errors to user
        },
        importContribsFromParent() {
            //TODO: Import contributors from parent
            console.log('Imported contributors!');
        },
        addAllContributors() {
            // Select all available search results, and add them to the list of people who will be added to the project (pending additional options)
            // was addAll in contribAdder.js
            let users = this.get('usersFound').filterBy('isContributor', false);
            this.get('contribsToAdd').addObjects(users);
        },
        addOneContributor(user) {
            // Add the specified search result to the list of users who will be added to the project (pending additional options)
            // Was $root.add
            this.get('contribsToAdd').addObject(user);
        },
        removeAllContributors() {
            // Clears the list of people who would be added to the project
            this.get('contribsToAdd').clear();
        },
        removeOneContributor(user) {
            // Was $root.remove.
            // Remove the specified search result from the list of users who will be added to the project (pending additional options)
            this.get('contribsToAdd').removeObject(user);
        },
        submitContributors() {
            // Intended to work with the addContributor action of `NodeActionsMixin`
            // TODO: This would benefit from bulk support. Error handling mechanism should deal with one/all requests failing
            let contribsToAdd = this.get('contribsToAdd');
            contribsToAdd.forEach((item) => {
                this.attrs.addContributor(item.get('id'), item.get('selectedPermission'), true)
                    .then(() => {
                        item.set('isContributor', true);
                        this.send('removeOneContributor', item);
                        // TODO: Hacky way of closing the modal, will bypass any closeAction cleanup specified to bs-modal
                        // TODO: Investigate submitAction for this use case. Implement that based on UI decision for showing errors.
                        this.set('isOpen', false);

                    });
            });
        },
        submitInvite() {
            // TODO: Not currently implemented pending required APIv2 capabilities
            console.log('User invited!');
        }
    }
});
