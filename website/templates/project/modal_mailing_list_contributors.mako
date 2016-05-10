<link rel="stylesheet" href="/static/css/mailing-list-modal.css">
<div class="modal fade" id="mailingListContributorsModal">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
              <h3>Project mailing list email</h3>
            </div>

            <div class="modal-body">
                <h4 class="row text-center">
                <div class="btn-group">
                    <a href="mailto: ${node['mailing_list_address']}">${node['mailing_list_address']}</a>
                </div>
                </h4>
                
                % if len(node['mailing_list_unsubs']):
                    <p>${len(node['contributors']) - len(node['mailing_list_unsubs'])} out of ${len(node['contributors'])} contributors will receive any email sent to this address.</p>
                    <p>A contributor who is not subscribed to this mailing list will not receive any emails sent to it. To
                    % if user['is_admin']:
                        disable or 
                    % endif:
                        unsubscribe from this mailing list, visit the <a href="${node['url']}settings/#configureNotificationsAnchor" class="">${node['category']} settings</a>.
                    </p>
                    <div class="padded-list contrib-list">
                        Contributors not on this list: 
                        <a id="unsubToggle" role="button" data-toggle="collapse" href="#unsubContribs" aria-expanded="false" aria-controls="unsubContribs">
                            Show
                        </a>
                        <div id="unsubContribs" class="panel-collapse collapse" role="tabpanel" aria-expanded="false" aria-labelledby="unsubToggle">
                        % for each in node['mailing_list_unsubs']:
                            <div class="padded-list">
                               ${each}
                            </div>
                        % endfor
                        </div>
                    </div>
                % else:
                    <br/>
                    <p>All contributors are subscribed and will receive any email sent to this address.</p>
                % endif

            </div><!-- end modal-body -->

            <div class="modal-footer">

                <a href="#" class="btn btn-default" data-dismiss="modal">Close</a>

            </div><!-- end modal-footer -->
        </div><!-- end modal-content -->
    </div><!-- end modal-dialog -->
</div><!-- end modal -->

<script>
$(document).ready(function() {
    $('#unsubContribs').on('hide.bs.collapse', function () {
        $('#unsubToggle').text('Show');
    });
    $('#unsubContribs').on('show.bs.collapse', function () {
        $('#unsubToggle').text('Hide');
    });
});
</script>
