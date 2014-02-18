<%inherit file="project/addon/node_settings.mako" />

% if user_has_auth and is_owner and bucket_list:

    <div class="form-group">
        <div class="well well-sm">Authorized by <a href="${owner_url}">${owner}</a></div>

        <input type="hidden" id="s3_bucket" value="${bucket}" name="s3_bucket" />

        <div class="btn-group">
          <button type="button" class="btn btn-default">
            <span id="bucketlabel" data-bind="label">${bucket if bucket else 'Select a bucket'}</span>
          </button>
          <button type="button" class="btn btn-default dropdown-toggle" data-toggle="dropdown">
            <span class="caret"></span>
          </button>

          <ul class="dropdown-menu pull-right" role="menu">
            <li role="presentation" class="dropdown-header">Your buckets</li>
            ${bucket_list}
            <li role="presentation" class="divider"></li>
            <li role="presentation"><a href="#"><i class="glyphicon glyphicon-plus"></i> Create a new bucket</a></li>
            <li role="presentation"><a href="/settings/#configureAddons"><i class="glyphicon glyphicon-remove"></i> Deauthorize</a></li>
          </ul>

        </div>

    </div>

% elif user_has_auth and is_owner:

    <div class="well well-sm">
        Updating settings. Please refresh the page in a moment to view your buckets.
    </div>

% elif user_has_auth:

    <div class="well well-sm">Authorized by <a href="${owner_url}">${owner}</a></div>
    <div class="btn-group btn-input">
      <button type="button" class="btn btn-default dropdown-toggle form-control" data-toggle="dropdown" disabled>
        <span id="bucketlabel" data-bind="label">${bucket if bucket else 'Select a bucket'}</span> <span class="caret"></span>
      </button>
    </div>

% else:

    <div class="form-group">
      <label for="s3Addon">Access Key</label>
        <input class="form-control" id="access_key" name="access_key" />
      </div>
      <div class="form-group">
        <label for="s3Addon">Secret Key</label>
        <input type="password" class="form-control" id="secret_key" name="secret_key" />
    </div>

% endif

%if user_has_auth:
    <script src="/addons/static/s3/s3-node-settings.js"></script>
    <script type="text/javascript">
        var addonShortname = '${addon_short_name}';
        setDropDownListener();
    </script>
%endif

<%def name="submit_btn()">
  %if not user_has_auth and is_owner:
    <button class="btn btn-success addon-settings-submit">
        Submit
    </button>
  %endif

</%def>

<%def name="on_submit()">

  %if not user_has_auth and is_owner:
    <script type="text/javascript">
      $(document).ready(function() {
         $('#addonSettings${addon_short_name.capitalize()}').on('submit', function() {

        var $this = $(this);
        var addon = $this.attr('data-addon');
        var msgElm = $this.find('.addon-settings-message');

        var url = nodeApiUrl + addon + '/authorize/';

        $.ajax({
            url: url,
            data: JSON.stringify(AddonHelper.formToObj($this)),
            type: 'POST',
            contentType: 'application/json',
            dataType: 'json'
        }).done(function() {
            msgElm.text('Settings updated')
                .removeClass('text-danger').addClass('text-success')
                .fadeOut(100).fadeIn();
                window.location.reload();
        }).fail(function(xhr) {
            var message = 'Error: ';
            var response = JSON.parse(xhr.responseText);
            if (response && response.message) {
                message += response.message;
            } else {
                message += 'Settings not updated.'
            }
            msgElm.text(message)
                .removeClass('text-success').addClass('text-danger')
                .fadeOut(100).fadeIn();
        });

        return false;
      });

    });
    </script>
  %else:
    ${parent.on_submit()}
  %endif

</%def>
