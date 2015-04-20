var page = require('web[page').create();

page.open(url, function(status){
    if(status == 200)
    {
        var content = page.content;
    }
    return content;
    })