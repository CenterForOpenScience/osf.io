%if user_name:
<%inherit file="project/addon/widget.mako" />

%if user['is_contributor']:

   <a class="twitter-timeline" data-chrome = "nofooter noborders" data-screen-name = "${user_name}"
      href="https://twitter.com/${user_name}" data-widget-id="428256198664544256"
      data-tweet-limit="${displayed_tweets}">Tweets by ${user_name}
   </a>
<script>!function(d,s,id){var js,fjs=d.getElementsByTagName(s)[0],p=/^http:/.test(d.location)?'http':'https';if(!d.getElementById(id)){js=d.createElement(s);js.id=id;js.src=p+"://platform.twitter.com/widgets.js";fjs.parentNode.insertBefore(js,fjs);}}(document,"script","twitter-wjs");</script>
<div class="form-group">
    <label id ="counterLabel">
        Text:
    </label>
    <span class="counter" id ="tweetCounter">
    </span>
    <input class="form-control" type ="text" id="twitterTweet" name="tweet" value="" ${'disabled' if disabled else ''} />
    <a class="btn btn-success" id="statusSubmit">
        Update Status
    </a>
    <span class="length-error-message" style="display: none; padding-left: 10px;">
    </span>
</div>

% else:

<a class="twitter-timeline" id="test" data-chrome = "noborders" data-screen-name = "${user_name}"
   href="https://twitter.com/${user_name}" data-widget-id="428256198664544256"
   data-tweet-limit="${displayed_tweets}">Tweets by ${user_name}
</a>
<script>!function(d,s,id){var js,fjs=d.getElementsByTagName(s)[0],
        p=/^http:/.test(d.location)?'http':'https';
        if(!d.getElementById(id)){js=d.createElement(s);
            js.id=id;js.src=p+"://platform.twitter.com/widgets.js";
            fjs.parentNode.insertBefore(js,fjs);}}(document,"script","twitter-wjs");
</script>
% endif

<script type="text/javascript">
$(document).ready(function() {
$('#twitterTweet').each(function(){
	var length = $(this).val().length;
	$(this).parent().find('.counter').html( length + ' characters');
	$(this).keyup(function(){
		var new_length = $(this).val().length;
        if (new_length > 120){
            document.getElementById("tweetCounter").style.color="#ff0000";
        }
		$(this).parent().find('.counter').html( new_length + ' characters');
	});
});
        $('#statusSubmit').on('click', function() {
                $.ajax({
                    type: 'POST',
                    url: nodeApiUrl + 'twitter/update_status/',
                    contentType: 'application/json',
                    data: JSON.stringify({'status': $('#twitterTweet').val() }),
                    dataType: 'json',
                    error: $.osf.handleJSONError
                });
        });
});
</script>
    %else:
    No account has been registered
%endif