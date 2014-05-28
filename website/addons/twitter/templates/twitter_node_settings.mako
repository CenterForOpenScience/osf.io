    <%inherit file="../../project/addon/node_settings.mako" />

<!-- Authorization -->
<div>
    <div class="alert alert-danger alert-dismissable">
    <button type="button" class="close" data-dismiss="alert" aria-hidden="true">&times;</button>
        Authorizing this Twitter add-on will grant all contributors on this feed
        permission to view your account.  Only the user that registers the account will be able to send tweets
        from the account.
    </div>
    <div class="alert alert-danger alert-dismissable">
        <button type="button" class="close" data-dismiss="alert" aria-hidden="true">&times;</button>
        If one of your collaborators removes you from this feed,
        your authorization for Twitter will automatically be revoked.
    </div>
    % if authorized_user:
        <a id="twitterDelKey" class="btn btn-danger">Unauthorize: Delete Access Token</a>
        <a class = "btn btn-primary">Authorized by @${authorized_user}</a>
        <div class="form-group">
            <label for="twitterUser">Enter # tweets to display on dashboard</label>
            <input class="form-control" type = "number" id="displayed_tweets" name="displayed_tweets" value="${displayed_tweets}" ${'disabled' if disabled else ''} />
         </div>
        <div class="form-group" id ="twitter_logs" name ="twitter_logs">
            <p>Select any events you want to tweet, and enter a custom message.  When the event occurs,
               a tweet will automatically be added to your 'tweet queue.'  Access this queue from your dashboard to
                send, edit, and delete these messages.
            </p>
            % for action in POSSIBLE_ACTIONS:
                <%   parsed_action_list = action.split('_')%>
                <%   parsed_action = ''.join((parsed_action_list[0],' ',parsed_action_list[1])) %>
                <%   parsed_action = parsed_action.title() %>
                <%   DEFAULT_MESSAGE = DEFAULT_MESSAGES.get(action) %>
            <label>
                <input id= "${action}" name="${action}" type="checkbox" ${'checked="checked"' if action in log_actions \
                else ''}>${parsed_action}

                <input name = "${action}_message"   class = "${action}_message" value =
                "${ log_messages.get(action+'_message', DEFAULT_MESSAGE) }" ${'type="text"' \
                if action in log_actions else 'hidden'} >
            </label>
            </br>
            % endfor
            <hr>
        </div>

        </br>

    % else:
        <a id="twitterAddKey" class="btn btn-primary">
            % if user_has_authorization:
                Authorize: Import Token from Profile
            % else:
                Authorize: Create Access Token
            % endif

        </a>
    % endif
</div>
<br/>

<script type="text/javascript">

    $(document).ready(function() {

        $('#twitterAddKey').on('click', function() {
            % if authorized_user:
                $.ajax({
                    type: 'POST',
                    url: nodeApiUrl + 'twitter/user_auth/',
                    contentType: 'application/json',
                    dataType: 'json',
                    success: function(response) {
                        window.location.reload();
                    }
                });
            % else:
                window.location.href = nodeApiUrl + 'twitter/oauth/';
            % endif
        });

        $('#twitter_logs :checkbox').click(function(){
            var $this = $(this);
            var $id = this.id;
            var $message_id = $id + '_message';
            if ($this.is(':checked')){
                $('.'+$message_id).show();
            }
            else {
                 $('.'+$message_id).hide();
            }
        });



        $('#twitterDelKey').on('click', function() {
            bootbox.confirm(
                'Are you sure you want to delete your Twitter access key?',
                function(result) {
                    if (result) {
                        $.ajax({
                            url: nodeApiUrl + 'twitter/oauth/delete/',
                            type: 'POST',
                            contentType: 'application/json',
                            dataType: 'json',
                            success: function() {
                                window.location.reload();
                            }
                        });
                    }
                }
            )
        });
    });

</script>
