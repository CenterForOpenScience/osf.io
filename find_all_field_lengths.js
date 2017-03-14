

function findMax() {

    var dbs = [];
    db.getCollectionNames().forEach(function (coll_name) {
        dbs.push(coll_name);
    });

    for (var k = 0; k < dbs.length; k++) {
        key = dbs[k];
        var lengths = {};
        db[key].find().forEach(function (doc) {
            for (field_name in doc) {
                if(lengths.hasOwnProperty(field_name)) {
                    if (doc[field_name] !== null && doc[field_name].length > lengths[field_name]) {
                        lengths[field_name] = doc[field_name].length;
                    }
                } else {
                    if (doc[field_name] !== null) {
                        lengths[field_name] = doc[field_name].length
                    }
                }
            }
        });
        print('Key: ' + key + '.' + field_name + ' ' + ' Length: ' + lengths[field_name]);
    }
}


use osf20130903
findMax();
