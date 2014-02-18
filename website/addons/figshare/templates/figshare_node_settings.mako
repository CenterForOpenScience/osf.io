<%inherit file="project/addon/node_settings.mako" />

<!-- Authorization -->
<div class="alert alert-danger alert-dismissable">
    <button type="button" class="close" data-dismiss="alert" aria-hidden="true">&times;</button>
        Authorizing this FigShare add-on will grant all contributors on this ${node['category']}
        permission to upload, modify, and delete files on the associated FigShare ${figshare_type}.
    </div>
<div class="alert alert-danger alert-dismissable">
        <button type="button" class="close" data-dismiss="alert" aria-hidden="true">&times;</button>
        If one of your collaborators removes you from this ${node['category']},
        your authorization for FigShare will automatically be revoked.
</div>
<div>
% if authorized_user:
        <a id="figshareDelKey" class="btn btn-danger">Unauthorize: Delete Access Token</a>
        <span>Authorized by ${authorized_user}</span>
% else:
        <a id="figshareAddKey" class="btn btn-primary">
            % if user_has_authorization:
               Authorize: Import Token from Profile
            % else:
                Authorize: Create Access Token
            % endif
        </a>
% endif
</div>

<br />

<div class="form-group">    
    % if figshare_id != '':
      <label for="figshareId">FigShare ${figshare_type.capitalize()}:</label><br />
      <a id="figshareRemoveLinked" class="btn btn-warning">${"Remove {0} {1}".format(figshare_type.capitalize(), figshare_id)}</a>
    % else:
      <label for="figshareId">FigShare Article ${"or Project " if authorized_user else ""} URL</label>	
      <input class="form-control" id="figshareId" name="figshare_id" value="" />
    % endif
</div>

<br />

<script type="text/javascript">

    $(document).ready(function() {    				 				 

        $('#figshareAddKey').on('click', function() {
            % if authorized_user:
                $.ajax({
                    type: 'POST',
                    url: nodeApiUrl + 'figshare/user_auth/',
                    contentType: 'application/json',
                    dataType: 'json',
                    success: function(response) {
                        window.location.reload();
                    }
                });
            % else:
                window.location.href = nodeApiUrl + 'figshare/oauth/';
            % endif
        });

        $('#figshareDelKey').on('click', function() {
            bootbox.confirm(
                'Are you sure you want to delete your Figshare access key? This will ' +
                    'revoke the ability to modify and upload files to Figshare. If ' +
                    'the associated repo is private, this will also disable viewing ' +
                    'and downloading files from Figshare.',
                function(result) {
                    if (result) {
                        $.ajax({
                            url: nodeApiUrl + 'figshare/oauth/delete/',
                            type: 'POST',
                            contentType: 'application/json',
                            dataType: 'json',
                            success: function() {
                                window.location.reload();
                            }
                        });
                    }
                }
            );
        });
	
	$('#figshareRemoveLinked').on('click', function(){
	    bootbox.confirm(
		'Are you sure you want to remove the linked Figshare ${figshare_type}?',
		function(result){
		  if(result){
			$.ajax({
			    url: nodeApiUrl + 'figshare/unlink/',
			    type: 'POST',
			    contentType: 'application/json',
                            dataType: 'json',
                            success: function() {
                                window.location.reload();
                            }
			});
		  }
		}
	    );				    
	});

    });

</script> 