<%inherit file="project/addon/widget.mako" />

%if user['is_contributor'] :

   <a class="twitter-timeline" data-chrome = "nofooter noborders" data-screen-name = "${user_name}" href="https://twitter.com/${user_name}" data-widget-id="428256198664544256" data-tweet-limit="${displayed_tweets}">Tweets by ${user_name}</a>
<script>!function(d,s,id){var js,fjs=d.getElementsByTagName(s)[0],p=/^http:/.test(d.location)?'http':'https';if(!d.getElementById(id)){js=d.createElement(s);js.id=id;js.src=p+"://platform.twitter.com/widgets.js";fjs.parentNode.insertBefore(js,fjs);}}(document,"script","twitter-wjs");</script>
 <div class="form-group">

    <input class="form-control" type ="text" id="twitterTweet" name="tweet" value="" ${'disabled' if disabled else ''} />
  <a class="btn btn-success" id="statusSubmit">Update Status</a>

  <span class="length-error-message" style="display: none; padding-left: 10px;"></span>

    </div>

% else:

<a class="twitter-timeline" id="test" data-chrome = "noborders" data-screen-name = "${user_name}" href="https://twitter.com/${user_name}" data-widget-id="428256198664544256" data-tweet-limit="${displayed_tweets}">Tweets by ${user_name}</a>
<script>!function(d,s,id){var js,fjs=d.getElementsByTagName(s)[0],p=/^http:/.test(d.location)?'http':'https';if(!d.getElementById(id)){js=d.createElement(s);js.id=id;js.src=p+"://platform.twitter.com/widgets.js";fjs.parentNode.insertBefore(js,fjs);}}(document,"script","twitter-wjs");</script>

% endif


<script type="text/javascript">

$(document).ready(function() {

        $('#statusSubmit').on('click', function() {
               // bootbox.confirm(
                //'Are you sure you want to delete your Twitter access key?',
         //       var len = $('#twitterTweet').val().length;
           //     var characters_over = len - 140;
              //  var  $this = $(this),
                //     msgElm = $this.find('.length-error-message');
/*
                     $.ajax({
                    type: 'POST',
                    url: nodeApiUrl + 'twitter/update_status/',
                    contentType: 'application/json',
                    data: JSON.stringify({'status': $('#twitterTweet').val() }),
                    dataType: 'json',
                    complete: function() {
                    alert('Tweet is too long by '+ len + ' characters' );
                     // window.location.reload();
                    msgElm.text('Settings updated')
                    .removeClass('text-danger').addClass('text-success')
                    .fadeOut(100).fadeIn();
                    }
                });


*/
                $.ajax({
                    type: 'POST',
                    url: nodeApiUrl + 'twitter/update_status/',
                    contentType: 'application/json',
                    data: JSON.stringify({'status': $('#twitterTweet').val() }),
                    dataType: 'json',
                    complete: function() {
                    alert('Tweet Posted!');
                      window.location.reload();
                    }
                });



        });
});


</script>