import Ember from 'ember';

export default Ember.Component.extend({
    permissionChanges: {},
    bibliographicChanges: {},
    actions: {
        permissionChange(contributor, permission) {
            this.set(`permissionChanges.${contributor.id}`, permission);
        },
        bibliographicChange(contributor, isBibliographic) {
            this.set(`bibliographicChanges.${contributor.id}`, isBibliographic);
        },
        updateContributors() {
            this.sendAction(
                'editContributors',
                this.get('contributors'),
                this.get('permissionChanges'),
                this.get('bibliographicChanges')
            );
        }
    }
});
