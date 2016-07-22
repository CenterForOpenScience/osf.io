import Ember from 'ember';

export default Ember.Component.extend({
    permissionChanges: {},
    bibliographicChanges: {},
    changed: false,
    canSubmit: false,
    actions: {
        permissionChange(contributor, contributors, permission) {
            this.set(`permissionChanges.${contributor.id}`, permission);
            this.set('changed', this.attributesChanged(contributors));
        },
        bibliographicChange(contributor, contributors, isBibliographic) {
            this.set(`bibliographicChanges.${contributor.id}`, isBibliographic);
            this.set('changed', this.attributesChanged(contributors));
        },
        updateContributors() {
            this.sendAction(
                'editContributors',
                this.get('contributors'),
                this.get('permissionChanges'),
                this.get('bibliographicChanges')
            );
        }
    },
    attributesChanged: function(contributors) {
        var _this = this;
        var changed = false;
        contributors.content.canonicalState.forEach(function(contrib) {
            var changedAttribute = _this.get('permissionChanges')[contrib.id];
            if (changedAttribute && contrib._data.permission !== changedAttribute) {
                changed = true;
            }
            var changedAttribute = _this.get('bibliographicChanges')[contrib.id];
            if (changedAttribute !== undefined && contrib._data.bibliographic !== changedAttribute) {
                changed = true;
            }
        });
        return changed;
    },
});
