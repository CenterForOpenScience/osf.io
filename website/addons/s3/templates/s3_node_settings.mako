<%inherit file="project/addon/node_settings.mako" />

%if user_has_auth:
    <div class="form-group">
        <label for="s3_bucket">Bucket Name</label>
        <input class="form-control" id="s3_bucket" name="s3_bucket" value="${bucket}" ${'disabled' if disabled or node_auth else ''}/>


        <div class="btn-group btn-input">
          <button type="button" class="btn btn-default dropdown-toggle form-control" data-toggle="dropdown" ${'disabled' if disabled or node_auth else ''}>
            <span data-bind="label">${bucket if bucket else 'Select a bucket'}</span> <span class="caret"></span>
          </button>
          <ul class="dropdown-menu" role="menu">
            ${bucket_list}
            <li role="presentation" class="divider"></li>
            <li role="presentation" class="dropdown-header">Or</li>
            <li><a>Create a new bucket</a></li>
          </ul>
        </div>


    </div>
%else:
    Amazon Simple Storage Service add-on is not configured properly.
    <br>
    Configure this add-on on the <a href="/settings/">settings</a> page, or click <a class="widget-disable" href="${node['api_url']}s3/settings/disable/">here</a> to disable it.
    <br>

%endif

<script type="text/javascript">
    $( document.body ).on( 'click', '.dropdown-menu li', function( event ) {

   var $target = $( event.currentTarget );

   $target.closest( '.btn-group' )
      .find( '[data-bind="label"]' ).text( $target.text() )
         .end()
      .children( '.dropdown-toggle' ).dropdown( 'toggle' );

   return false;

});
</script>

<%def name="submit_btn()">
    %if user_has_auth and node_auth:
        <button class="btn btn-danger addon-settings-submit">
            Remove Access
        </button>

    %elif user_has_auth:
        <button class="btn btn-success addon-settings-submit">
        Submit
        </button>
    %else:

    %endif
</%def>

##TODO in an external js file

##TODO Load this after successful submit.... Somehow

<%def name="on_submit()">
    %if node_auth:
        <script type="text/javascript">
        var force = ''
         $(document).ready(function() {
            $('#addonSettings${addon_short_name.capitalize()}').on('submit', function() {
                var $this = $(this),
                addon = $this.attr('data-addon'),
                msgElm = $this.find('.addon-settings-message');
                $.ajax({
                    url: nodeApiUrl + '${addon_short_name}' + '/settings/delete/' + force,
                    type: 'POST',
                    contentType: 'application/json',
                    dataType: 'json',
                }).success(function() {
                    msgElm.text('Access removed')
                        .removeClass('text-danger').addClass('text-success')
                        .fadeOut(100).fadeIn();
                }).fail(function(xhr) {
                    var message = 'Error: Access not removed';
                    msgElm.text(message)
                        .removeClass('text-success').addClass('text-danger')
                        .fadeOut(100).fadeIn();
                    btn = $this.find('.addon-settings-submit');
                    btn.text('Force Removal');
                    btn.attr('class', 'btn btn-warning addon-settings-submit')
                    force = 'force/';
                });
                return false;
            });
        });
        </script>
    %else:
        ${parent.on_submit()}
    %endif
</%def>
