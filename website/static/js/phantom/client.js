/**
 * Created by kushagragupta on 4/22/15.
 */

module.exports = {
    waitForMySignal: function(time) {
        if(typeof(window.callPhantom) == "function") {
            window.callPhantom('spectre.Wait', time);
        }
    },
    signal: function() {
        if(typeof(window.callPhantom) == "function") {
            window.callPhantom('spectre.Done');
        }
    }
};