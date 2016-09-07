

function findMax() {
    var max = 0;

    db.nodewikipage.find().forEach(function(doc) {
        var currentLength = doc.page_name.length;
        if (currentLength > max) {
           max = currentLength;
        }
    });

    print(max);
}

use osf20130903
findMax();
