/**
 * Helper method that converts jquery deferred into an ember-style promise. Facilitates chaining with manual AJAX calls.
 * @class deferredPromise
 * @param {$.Deferred}
 * @returns {boolean}
 */
export default function deferredPromise(jqDeferred) {
  return new Ember.RSVP.Promise((resolve, reject) => {
        // TODO: Improve param capture
        jqDeferred.done((value) => resolve(value));
        jqDeferred.fail((reason) => reject(reason));
    });
}
