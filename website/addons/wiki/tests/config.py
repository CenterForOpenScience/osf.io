EXAMPLE_DOCS = {
    "_id": "9a247ce9-b219-5f7d-b2c8-ef31661b38d7",
    "data": {
        "v": 20,
        "meta": {
            "mtime": 1413229471447.0,
            "ctime": 1413229471447.0,
        },
        "snapshot": "one two three four! ",
        "type": "text",
    }
}

# Collection stored as "ops.9a247ce9%2Db219%2D5f7d%2Db2c8%2Def31661b38d7"
EXAMPLE_OPS = [
    { "opData" : { "op" : [  {  "p" : 0,  "i" : "o" } ], "meta" : { "source" : "8980f013f3aff79a7e413634c1c31337", "ts" : 1413229501733.0 } }, "_id" : 0 },
    { "opData" : { "op" : [  {  "p" : 1,  "i" : "n" } ], "meta" : { "source" : "8980f013f3aff79a7e413634c1c31337", "ts" : 1413229501981.0 } }, "_id" : 1 },
    { "opData" : { "op" : [  {  "p" : 2,  "i" : "e" } ], "meta" : { "source" : "8980f013f3aff79a7e413634c1c31337", "ts" : 1413229502296.0 } }, "_id" : 2 },
    { "opData" : { "op" : [  {  "p" : 3,  "i" : " " } ], "meta" : { "source" : "8980f013f3aff79a7e413634c1c31337", "ts" : 1413229502878.0 } }, "_id" : 3 },
    { "opData" : { "op" : [  {  "p" : 4,  "i" : "t" } ], "meta" : { "source" : "8980f013f3aff79a7e413634c1c31337", "ts" : 1413229503430.0 } }, "_id" : 4 },
    { "opData" : { "op" : [  {  "p" : 5,  "i" : "w" } ], "meta" : { "source" : "8980f013f3aff79a7e413634c1c31337", "ts" : 1413229503878.0 } }, "_id" : 5 },
    { "opData" : { "op" : [  {  "p" : 6,  "i" : "o" } ], "meta" : { "source" : "8980f013f3aff79a7e413634c1c31337", "ts" : 1413229504329.0 } }, "_id" : 6 },
    { "opData" : { "op" : [  {  "p" : 7,  "i" : " " } ], "meta" : { "source" : "8980f013f3aff79a7e413634c1c31337", "ts" : 1413229505782.0 } }, "_id" : 7 },
    { "opData" : { "op" : [  {  "p" : 8,  "i" : "t" } ], "meta" : { "source" : "8980f013f3aff79a7e413634c1c31337", "ts" : 1413229506818.0 } }, "_id" : 8 },
    { "opData" : { "op" : [  {  "p" : 9,  "i" : "h" } ], "meta" : { "source" : "8980f013f3aff79a7e413634c1c31337", "ts" : 1413229507215.0 } }, "_id" : 9 },
    { "opData" : { "op" : [  {  "p" : 10,  "i" : "r" } ], "meta" : { "source" : "8980f013f3aff79a7e413634c1c31337", "ts" : 1413229507621.0 } }, "_id" : 10 },
    { "opData" : { "op" : [  {  "p" : 11,  "i" : "e" } ], "meta" : { "source" : "8980f013f3aff79a7e413634c1c31337", "ts" : 1413229508103.0 } }, "_id" : 11 },
    { "opData" : { "op" : [  {  "p" : 12,  "i" : "e" } ], "meta" : { "source" : "8980f013f3aff79a7e413634c1c31337", "ts" : 1413229508749.0 } }, "_id" : 12 },
    { "opData" : { "op" : [  {  "p" : 13,  "i" : " " } ], "meta" : { "source" : "8980f013f3aff79a7e413634c1c31337", "ts" : 1413229509287.0 } }, "_id" : 13 },
    { "opData" : { "op" : [  {  "p" : 14,  "i" : "f" } ], "meta" : { "source" : "8980f013f3aff79a7e413634c1c31337", "ts" : 1413229509933.0 } }, "_id" : 14 },
    { "opData" : { "op" : [  {  "p" : 15,  "i" : "o" } ], "meta" : { "source" : "8980f013f3aff79a7e413634c1c31337", "ts" : 1413229510398.0 } }, "_id" : 15 },
    { "opData" : { "op" : [  {  "p" : 16,  "i" : "u" } ], "meta" : { "source" : "8980f013f3aff79a7e413634c1c31337", "ts" : 1413229510991.0 } }, "_id" : 16 },
    { "opData" : { "op" : [  {  "p" : 17,  "i" : "r" } ], "meta" : { "source" : "8980f013f3aff79a7e413634c1c31337", "ts" : 1413229511639.0 } }, "_id" : 17 },
    { "opData" : { "op" : [  {  "p" : 18,  "i" : "!" } ], "meta" : { "source" : "8980f013f3aff79a7e413634c1c31337", "ts" : 1413229515472.0 } }, "_id" : 18 },
    { "opData" : { "op" : [  {  "p" : 19,  "i" : " " } ], "meta" : { "source" : "8980f013f3aff79a7e413634c1c31337", "ts" : 1413229516120.0 } }, "_id" : 19 },
    # Ops after this point are not contained in the snapshot
    { "opData" : { "op" : [  {  "p" : 20,  "i" : "x" } ], "meta" : { "source" : "8980f013f3aff79a7e413634c1c31337", "ts" : 1413229516927.0 } }, "_id" : 20 }
]

# sharejs data short enough to not have an entry in the "docs" collection
EXAMPLE_OPS_SHORT = [
    { "opData" : { "op" : [  {  "p" : 0,  "i" : "o" } ], "meta" : { "source" : "8980f013f3aff79a7e413634c1c31337", "ts" : 1413229501733.0 } }, "_id" : 0 },
    { "opData" : { "op" : [  {  "p" : 1,  "i" : "n" } ], "meta" : { "source" : "8980f013f3aff79a7e413634c1c31337", "ts" : 1413229501981.0 } }, "_id" : 1 },
    { "opData" : { "op" : [  {  "p" : 2,  "i" : "e" } ], "meta" : { "source" : "8980f013f3aff79a7e413634c1c31337", "ts" : 1413229502296.0 } }, "_id" : 2 },
    { "opData" : { "op" : [  {  "p" : 3,  "i" : " " } ], "meta" : { "source" : "8980f013f3aff79a7e413634c1c31337", "ts" : 1413229502878.0 } }, "_id" : 3 },
    { "opData" : { "op" : [  {  "p" : 4,  "i" : "t" } ], "meta" : { "source" : "8980f013f3aff79a7e413634c1c31337", "ts" : 1413229503430.0 } }, "_id" : 4 },
    { "opData" : { "op" : [  {  "p" : 5,  "i" : "w" } ], "meta" : { "source" : "8980f013f3aff79a7e413634c1c31337", "ts" : 1413229503878.0 } }, "_id" : 5 },
    { "opData" : { "op" : [  {  "p" : 6,  "i" : "o" } ], "meta" : { "source" : "8980f013f3aff79a7e413634c1c31337", "ts" : 1413229504329.0 } }, "_id" : 6 },
]