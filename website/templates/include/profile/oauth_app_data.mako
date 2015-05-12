<form role="form" method="post" action="${ web_url_for('oauth_application_register') }">
    <!-- TODO: Write AJAX or KO endpoint for submission -->
    <div class="form-group">
        <label>Application name</label>
        <input class="form-control" type="text" name="appName">
    </div>

    <div class="form-group">
        <label>Project homepage URL</label>
        <input class="form-control" type="text" name="appHomeURL">
    </div>

    <div class="form-group">
        <label>Application description</label>
        <textarea class="form-control" placeholder="Application description is optional" name="appDesc"></textarea>
    </div>

    <div class="form-group">
        <label>Authorization callback URL</label>
        <input type="text" class="form-control" placeholder="Is this field necessary for the OSF API?" name="appCallbackURL">
    </div>


    <div class="padded">
        <button type="submit" class="btn btn-primary">Submit</button>
    </div>
</form>
