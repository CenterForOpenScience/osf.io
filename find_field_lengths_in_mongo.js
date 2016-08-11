/*
  Finds the longest value in the database for the specific field. 

  Change "field_name" to the field name that you want the maximum length for
  then run =>

  $ mongo osf20130903 < find_field_lengths_in_mongo.js
*/

function findMax() {
    var max = 0;

    db.externalaccount.find().forEach(function(doc) {
        var currentLength = doc.field_name.length;
        if (currentLength > max) {
           max = currentLength;
        }
    });

     print(max);
}

use osf20130903
findMax();
