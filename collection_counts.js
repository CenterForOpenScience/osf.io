
function findCounts() {
    var dbs = [];
    db.getCollectionNames().forEach(function (coll_name) {
        dbs.push(coll_name);
    });

    for (var k = 0; k < dbs.length; k++) {
        key = dbs[k];
        count = db[key].find().count();
        print(db[key] + ': ' + count);
    }
}

findCounts();
