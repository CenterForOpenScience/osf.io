// main.js
$(function(){
var client = new ZeroClipboard( document.getElementsByClassName("copy-button") );

client.on( "load", function(client) {
  // alert( "movie is loaded" );

  client.on( "complete", function(client, args) {
    // `this` is the element that was clicked
  } );
} );

});