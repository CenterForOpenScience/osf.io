<form role="form" method="post" action="${ web_url_for('oauth_application_register') }">
    <!-- TODO: Write AJAX or KO endpoint for submission -->
    <div class="form-group">
        <label>Application name</label>
        <input class="form-control" type="text" name="appName" value="${app_data['client_id'] if app_data is not None else ''}">
    </div>

    <div class="form-group">
        <label>Project homepage URL</label>
        <input class="form-control" type="text" name="appHomeURL" value="${app_data['home_url'] if app_data is not None else ''}">
    </div>

    <div class="form-group">
        <label>Application description</label>
        <textarea class="form-control" placeholder="Application description is optional" name="appDesc">${app_data['description'] if app_data is not None else ''}</textarea>
    </div>

    <div class="form-group">
        <label>Authorization callback URL</label>
        <input type="text" class="form-control" name="appCallbackURL" value="${app_data['callback_url'] if app_data is not None else ''}">
    </div>


    <div class="padded">
        <button type="submit" class="btn btn-primary">Submit</button>
    </div>
</form>
