

function findMax() {
    var max = 0;

    db.notificationsubscription.find().forEach(function(doc) {
        var currentLength = doc.event_name.length;
        if (currentLength > max) {
           max = currentLength;
        }
    });

    print(max);
}

use osf20130903
findMax();
