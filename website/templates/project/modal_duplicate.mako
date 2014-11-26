% if not disk_saving_mode:

<div class="modal fade" id="duplicateModal">
##<pre data-bind="text: ko.toJSON($data, null, 2)"></pre>
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-body">
                <div class="row">
                    <div class="col-md-4">
                        <h4>Links
                            <button data-bind="
                                enable: showLinksAllowed(),
                                click: showLinks, 
                                attr: {class: showLinksAllowed() ? 'btn btn-primary' : 'well well-inline'},
                                css: 'pull-right',
                                text: node.points"></button>
                        </h4>
                        ${ language.LINK_DESCRIPTION }
                    </div>
                    <div class="col-md-4">
                        <h4>Templated From
                            <button data-bind="
                                enable: showTemplatesAllowed(), 
                                click: showTemplates, 
                                attr: {class: showTemplatesAllowed() ? 'btn btn-primary' : 'well well-inline'},
                                css: 'pull-right',
                                text: node.templated_count"></button>
                        </h4>
                        ${ language.TEMPLATE_DESCRIPTION }
                    </div>
                    <div class="col-md-4">
                        <h4>Forks
                            <button data-bind=" 
                            enable: showForksAllowed(),
                            click: showForks, 
                            attr: {class: showForksAllowed() ? 'btn btn-primary' : 'well well-inline'},
                            css: 'pull-right',
                            text: node.fork_count"></button>
                        </h4>
                        ${ language.FORK_DESCRIPTION }
                    </div>
                </div>
                <div class="row">
                    <div class="col-md-4">
##                      <button data-bind=" enable: { false } >${ language.LINK_ACTION }</button>
                    </div>
                    <div class="col-md-4">
                        <button data-bind=" 
                            enable:  primaryButtonsAllowed(),
                            attr: {class: primaryButtonsAllowed() ? 'btn btn-primary form-control' : 'disabled'}, 
                            click: useAsTemplate" 
                            data-dismiss="modal">${ language.TEMPLATE_ACTION }</button>
                    </div>
                    <div class="col-md-4">
                        <button data-bind="
                            enable:  primaryButtonsAllowed(),
                            attr: {class: primaryButtonsAllowed() ? 'btn btn-primary form-control' : 'disabled'},
                            click: forkNode"
                            data-dismiss="modal">${ language.FORK_ACTION }</button>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-default" data-dismiss="modal">Cancel</button>
            </div>
        </div><!-- /.modal-content -->
    </div><!-- /.modal-dialog -->
</div><!-- /.modal -->

## Alternate modal for when undergoing a disk upgrade.
% else:
<div class="modal fade" id="duplicateModal">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header">
                <h4 class="modal-title">Temporarily Disabled</h4>
            </div>
            <div class="modal-body">
                Forks and registrations are currently disabled while the OSF is undergoing a server upgrade. These features will return shortly.
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-default" data-dismiss="modal">OK</button>
            </div>
        </div><!-- /.modal-content -->
    </div><!-- /.modal-dialog -->
</div><!-- /.modal -->
% endif