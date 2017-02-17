

function findMax() {
    var max = 0;

    db.useractivitycounters.find().forEach(function(doc) {
        var currentLength = doc._id.length;
        if (currentLength > max) {
           max = currentLength;
        }
    });

    print(max);
}

use osf20130903
findMax();
