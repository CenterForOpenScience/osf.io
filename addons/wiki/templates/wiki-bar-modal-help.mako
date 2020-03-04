<div class="modal fade" id="wiki-help-modal" tabindex="-1" role="dialog" aria-labelledby="myModalLabel" aria-hidden="true">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true"></span>&times;</button>
                    <h3 class="modal-title">${_("Wiki syntax help")}</h3>
                </div>
                <div class="modal-body">
                  <p>
                    ${_('The wiki uses the <a %(mark_url)s>Markdown</a> syntax. For more information and examples, go to our <a %(zendesk_url)s>Guides.</a>') % dict(mark_url='href="https://daringfireball.net/projects/markdown/"', zendesk_url='href="https://openscience.zendesk.com/hc/en-us/sections/360003569274"') | n}
                  </p>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-primary" data-dismiss="modal">${_("Close")}</button>
                </div>
            </div>
        </div>
</div>
