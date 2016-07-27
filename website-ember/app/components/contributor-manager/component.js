import Ember from 'ember';

export default Ember.Component.extend({
    session: Ember.inject.service(),
    currentUser: Ember.inject.service(),
    permissionChanges: {},
    bibliographicChanges: {},
    changed: false,
    hasMinAdmins: true,
    hasMinBibliographic: true,
    isRegistration: Ember.computed(function() {
        return this.get('node').get('registration');
    }),
    canSubmit: Ember.computed('hasMinAdmins', 'hasMinBibliographic', 'changed', function() {
        return this.get('hasMinAdmins') && this.get('hasMinBibliographic') && this.get('changed');
    }),
    showModalRemoveContributors: false,
    showModalSaveContributors: false,
    canRemoveContributor: false,
    contributorToRemove: null,
    actions: {
        permissionChange(contributor, contributors, permission) {
            this.set(`permissionChanges.${contributor.id}`, permission);
            this.updateAttributes(contributors);
            if (contributor.get('permission') !== permission) {
                event.currentTarget.style['font-weight'] = 'normal';
            } else {
                event.currentTarget.style['font-weight'] = 'bold';
            }
        },
        bibliographicChange(contributor, contributors, isBibliographic) {
            this.set(`bibliographicChanges.${contributor.id}`, isBibliographic);
            this.updateAttributes(contributors);
        },
        updateContributors() {
            this.sendAction(
                'editContributors',
                this.get('contributors'),
                this.get('permissionChanges'),
                this.get('bibliographicChanges')
            );
        },
        cancel() {
            var _this = this;
            var contributors = _this.get('contributors');
            contributors.forEach(function(contrib) {
                Ember.$('tr#' + contrib.id + ' td.permissions select').val(contrib.get('permission'));
                Ember.$('tr#' + contrib.id + ' td.permissions select').attr('style', 'font-weight:bold');
                Ember.$('tr#' + contrib.id + ' td.bibliographic input')[0].checked = contrib.get('bibliographic');
            });
            this.set('hasMinAdmins', true);
            this.set('hasMinBibliographic', true);
            this.set('changed', false);
            this.set('permissionChanges', {});
            this.set('bibliographicChanges', {});
        },
        toggleRemoveContributorModal(contributor) {
            this.toggleProperty('showModalRemoveContributors');
            this.set('canRemoveContributor', this.contributorRemovalPrecheck(contributor, this.get('contributors')));
            this.set('contributorToRemove', contributor);
        },
        toggleSaveContributorModal() {
            this.toggleProperty('showModalSaveContributors');
        },
        removeContributor(contrib) {
            this.sendAction('removeContributor', contrib);
        },
    },
    updateAttributes: function(contributors) {
        var proposedChanges = this.checkProposedChanges(contributors);
        this.set('changed', proposedChanges.changed);
        proposedChanges.numAdmins > 0 ? this.set('hasMinAdmins', true) : this.set('hasMinAdmins', false);
        proposedChanges.numBibliographic > 0 ? this.set('hasMinBibliographic', true) : this.set('hasMinBibliographic', false);
    },
    checkProposedChanges: function(contributors) {
        var _this = this;
        var changed = false;
        var numAdmins = 0;
        var numBibliographic = 0;

        contributors.forEach(function(contrib) {
            var changedPermission = _this.get('permissionChanges')[contrib.id];
            var originalPermission = contrib.get('permission');
            if (changedPermission && (originalPermission !== changedPermission)) {
                changed = true;
                if (changedPermission === 'admin') {
                    numAdmins++;
                }
            } else {
                if (originalPermission === 'admin') {
                    numAdmins++;
                }
            }

            var changedBibliographic = _this.get('bibliographicChanges')[contrib.id];
            var originalBibliographic = contrib.get('bibliographic');
            if ((changedBibliographic !== undefined) && (originalBibliographic !== changedBibliographic)) {
                changed = true;
                if (changedBibliographic === true) {
                    numBibliographic++;
                }
            } else {
                if (originalBibliographic === true) {
                    numBibliographic++;
                }
            }
        });

        return {
            changed: changed,
            numAdmins: numAdmins,
            numBibliographic: numBibliographic
        };
    },
    contributorRemovalPrecheck: function(contributorToRemove, contributors) {
        var minAdmins = false;
        var minBibliographic = false;
        var minRegisteredContrib = false;
        contributors.forEach(function(contrib) {
            if (contrib.id !== contributorToRemove.id) {
                if (contrib.get('permission') === 'admin') {
                    minAdmins = true;
                }
                if (contrib.get('bibliographic') === true) {
                    minBibliographic = true;
                }
                if (contrib.get('unregisteredContributor') === null) {
                    minRegisteredContrib = true;
                }
            }
        });
        return minAdmins && minBibliographic && minRegisteredContrib;
    }
});
