<%inherit file="../../project/addon/node_settings.mako" />

<script src="/static/addons/s3/s3-node-settings.js"></script>

% if bucket_list is not None:

    % if node_has_auth:
        <div class="well well-sm">
            Authorized by <a href="${owner_url}">${owner}</a>
            <a id="s3RemoveToken" class="text-danger pull-right" style="cursor: pointer">Deauthorize</a>
        </div>
    % endif

    <div class="form-group">

        <div class="row">

            <div class="col-md-6">

                <select class="form-control" id="s3_bucket" name="s3_bucket" ${'' if user_has_auth and (owner is None or is_owner) and not is_registration else 'disabled'}>
                    <option value="">-----</option>
                    % for bucket_name in bucket_list or []:
                        <option value="${bucket_name}" ${'selected' if bucket_name == bucket else ''}>${bucket_name}</option>
                    % endfor
                </select>

            </div>

            % if user_has_auth and (owner is None or is_owner) and not is_registration:
                <div class="col-md-6">
                    <a class="btn btn-default" id="newBucket">Create Bucket</a>
                </div>
            % endif

        </div>

    </div> <!-- End form group -->

% elif user_has_auth and bucket_list is None:

    <div class="well well-sm">
        S3 access keys loading. Please wait a moment and refresh the page.
    </div>

% else:

    <div class="form-group">
        <label for="s3Addon">Access Key</label>
        <input class="form-control" id="access_key" name="access_key"/>
    </div>
    <div class="form-group">
        <label for="s3Addon">Secret Key</label>
        <input type="password" class="form-control" id="secret_key" name="secret_key"/>
    </div>

% endif

<%def name="on_submit()">

    % if not user_has_auth:

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

    % else:

        ${parent.on_submit()}

    % endif

</%def>
