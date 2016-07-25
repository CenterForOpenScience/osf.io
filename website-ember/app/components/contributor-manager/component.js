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
            contributors.content.canonicalState.slice(0).forEach(function(contrib, index) {
                $('tr#' + contrib.id + ' td.permissions select').val(contrib._data.permission);
                $('tr#' + contrib.id + ' td.permissions select').attr('style', 'font-weight:bold');
                $('tr#' + contrib.id + ' td.bibliographic input')[0].checked = contrib._data.bibliographic;
            });
            this.set('hasMinAdmins', true);
            this.set('hasMinBibliographic', true);
            this.set('changed', false);
            this.set('permissionChanges', {});
            this.set('bibliographicChanges', {});
        }
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

        contributors.content.canonicalState.slice(0).forEach(function(contrib, index) {
            var changedPermission = _this.get('permissionChanges')[contrib.id];
            var originalPermission = contrib._data.permission;
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
            var originalBibliographic = contrib._data.bibliographic;
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
    }
});
