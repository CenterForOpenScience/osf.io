%if user_name:
<%inherit file="project/addon/widget.mako" />

%if user['is_contributor']:

   <a class="twitter-timeline" data-chrome = "nofooter noborders" data-screen-name = "${user_name}"
      href="https://twitter.com/${user_name}" data-widget-id="428256198664544256"
      data-tweet-limit="${displayed_tweets}">
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

  <script>

$(document).ready(function(){
    function TweetModel(tweet, index) {
        var self = this;
        this.tweet = ko.observable(tweet);
}
    function TweetViewModel(){
        var self = this;
        someurl = '${node['api_url']}' + 'twitter/tweet_queue/';
        self.tweets = ko.observableArray([]);
        self.emptyTweetQueue = ko.observable(true);

        setTimeout(function(){
            $.getJSON(someurl, function(data){
                var viewModel = new TweetViewModel();
                $.each(data.key, function (i, val) {
                    var tweetModel = new TweetModel();
                    tweetModel.tweet = data.key[0];
                    tweetModel.index = i;
                    self.tweets.push(tweetModel);
                    viewModel.tweets.push(tweetModel);
                    self.emptyTweetQueue(false);
                })
            })
        }, 5000);
        self.removeTweet = function(tweet) {
             $.ajax({
                    type: 'POST',
                    url: nodeApiUrl + 'twitter/remove_queued_tweet/',
                    contentType: 'application/json',
                    data: JSON.stringify({'index': self.tweets.indexOf(tweet) }),
                    dataType: 'json',
                    error: $.osf.handleJSONError
                });
            self.tweets.remove(tweet);
        };

        self.queueSubmit = function(tweet) {
            console.log(tweet);
             $.ajax({
            type: 'POST',
            url: nodeApiUrl + 'twitter/send_queued_tweet/',
            contentType: 'application/json',
            data: JSON.stringify(
                    {
                     'status': tweet.tweet,
                     'index': self.tweets.indexOf(tweet)
                    }
            ),
            dataType: 'json',
            error: $.osf.handleJSONError
           });
        self.tweets.remove(tweet)
    };
    }
        ko.applyBindings(new TweetViewModel(), $('#foo')[0]);
});

  </script>
       <div id = "foo">
           <h4>Send, Edit, and Delete Tweets </h4>
           <div data-bind="visible: emptyTweetQueue">
               You currently have no tweets pending.
           </div>
        <!-- ko foreach: tweets.slice(0, 5) -->
            <input  style="width: 200px" data-bind="value: tweet"/>
            <a  class="btn btn-primary" data-bind="click: $parent.queueSubmit" >
                Send
            </a>
            <a class="btn btn-danger" data-bind = "click: $parent.removeTweet" >
                Delete
            </a>
           </br>
         <!-- /ko -->
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