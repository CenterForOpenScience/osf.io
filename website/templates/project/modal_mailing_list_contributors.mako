<div class="modal fade" id="discussionsContributorsModal">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
              <h3>Project Mailing List Email:</h3>
            </div>

            <div class="modal-body">
                <h3 style="text-align: center">${node['id']}@osf.io</h4>
                
                <p>${node['contrib_count'] - len(node['discussions_unsubs'])} out of ${node['contrib_count']} contributors will receive this email.</p>
                <p>A contributor who is not subscribed to this mailing list will not recieve any emails sent to it, but will still be able to send emails themselves. These emails will be distributed normally.</p>
                <div style="padding-left: 15px; background-color: #F5F5F5; border: 1px solid #CCC;">
                Contributors not on this list:</br>
                % for each in node['discussions_unsubs']:
                    <div style="padding-left: 15px">
                       ${each}
                    </div>
                % endfor
                </div>


            </div><!-- end modal-body -->

            <div class="modal-footer">

                <a href="#" class="btn btn-default" data-dismiss="modal">Cancel</a>
                <a href="${node['url']}settings/#configureNotificationsAnchor" class="btn btn-default">Change Settings</a>

            </div><!-- end modal-footer -->
        </div><!-- end modal-content -->
    </div><!-- end modal-dialog -->
</div><!-- end modal -->
