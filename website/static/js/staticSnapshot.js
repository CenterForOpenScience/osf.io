var page = require('webpage').create();
var system = require('system');
var args = system.args;
var url = args[1];

console.log(args[1]);

page.open(url, function(status){
    if(status == 'success')
    {
        var content = page.content;
        console.log(content);
        return content;
    }
    else
        console.log("status fail");
    phantom.exit();
    })