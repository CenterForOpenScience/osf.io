// main.js
$(function(){
var client = new ZeroClipboard( document.getElementsByClassName("copy-button") );

client.on( "load", function(client) {
  // alert( "movie is loaded" );

  client.on( "complete", function(client, args) {
    // `this` is the element that was clicked
      this.blur();
  } );

  client.on("mousedown", function(client,args){
      $(this).addClass("active");
  });

  client.on("mouseup",function(client,args){
      $(this).removeClass("active");
  });

  client.on("mouseover",function(client,args){
      $(this).tooltip("show");
  });

  client.on("mouseout",function(client,args){
      $(this).tooltip("hide");
  });
} );

});