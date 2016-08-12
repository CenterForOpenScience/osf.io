

function findMax() {
    var max = 0;

    db.apioauth2personaltoken.find().forEach(function(doc) {
        var currentLength = doc.scopes.length;
        if (currentLength > max) {
           max = currentLength;
        }
    });

    print(max);
}

use osf20130903
findMax();
