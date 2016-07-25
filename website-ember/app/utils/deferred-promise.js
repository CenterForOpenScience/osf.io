/**
 * Helper method that converts jquery deferred into an ember-style promise. Facilitates chaining with manual AJAX calls.
 * @class deferredPromise
 * @param {$.Deferred}
 * @returns {boolean}
 */
export default function deferredPromise(jqDeferred) {
  return new Ember.RSVP.promise((resolve, reject) => ){
        jqDeferred.done(() => resolve(...arguments));
        jqDeferred.fail(() => reject(...arguments));
    };
}
