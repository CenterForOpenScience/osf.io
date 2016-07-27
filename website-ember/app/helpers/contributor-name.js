import Ember from 'ember';

export function contributorName(params/*, hash*/) {
    var contributor = params[0];
    if (contributor) {
        var contributorName = contributor.get('users').get('fullName');
        if (contributor.get('unregisteredContributor')) {
            contributorName = contributor.get('unregisteredContributor');
        }
        return contributorName;
    } else {
        return params;
    }
}

export default Ember.Helper.helper(contributorName);
