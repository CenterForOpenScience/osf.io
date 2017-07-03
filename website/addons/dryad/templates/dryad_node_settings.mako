<div id="DryadStatusScope">

    <div id="dryadImportModal" class="modal fade">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">

                <div class="modal-header">
                    <h3>Importing Dryad Package to OSF Storage</h3>
                </div>


                <div class="modal-body">

                    <div class="row text-info" style="text-align: center">
                        <h4>Please don't close this window until the import is complete</h4>
                    </div><!-- end row -->


                    <div class="row" style="text-align: center">
                        <div class="logo-spin logo-lg"></div>
                    </div>
                    
                    <div class="row text-info" style="text-align: center">
                        <span class="help-block">
                            <p data-bind="text: message, attr.class: messageClass"></p>
                        </span>
                    </div>

                </div><!-- end modal-body -->
            </div><!-- end modal-content -->
        </div>
    </div>

    <h4 class="addon-title">
        <img class="addon-icon" src="${addon_icon_url}"></img>
        ${addon_full_name}
    </h4>
    <!--Status Sub Pane -->
    <div >
        <form data-bind="submit: setDOI">
            <span>
                <input id="dryaddoitext" type="text" data-bind="value: doi"
                    placeholder="10.5061/dryad.XXXX">
            </span>
            <span>
            <button class="btn btn-success addon-settings-submit">
                Import
            </button>
            </span>
        </form>
        </br>
        <span class="help-block">
            <p data-bind="text: message, attr.class: messageClass"></p>
        </span>

        <div class="panel panel-default" >
            <div class="panel-heading clearfix">
                <h3 class="panel-title">
                    Current Package
                </h3>
                <div class="pull-right">
                    <button class="btn btn-link project-toggle">
                        <i class="fa fa-angle-down"></i>
                    </button>
                </div>
            </div>
            <div class="panel-body"
                 style="display:none;max-height:500px;overflow:auto;">
                <%include file="dryad_status.mako"/>
            </div>
        </div>
    </div>

    <!-- Browser Sub-Pane -->
    <div id="DryadBrowserScope" class="panel panel-default" >
        <div class="panel-heading clearfix">
            <h3 class="panel-title">
                Browse/Search Packages
            </h3>
            <div class="pull-right">
                <button class="btn btn-link project-toggle">
                    <i class="fa fa-angle-down"></i>
                </button>
            </div>
        </div>
        <div class="panel-body"
             style="display:none;max-height:500px;overflow:auto;">
            <%include file="dryad_browser.mako"/>
        </div>
    </div>

    <!-- Citation  Sub Pane-->
    <div id="DryadCitationScope" class="panel panel-default">
        <div class="panel-heading clearfix">
            <h3 class="panel-title">
                Citation
            </h3>
            <div class="pull-right">
                <button class="btn btn-link project-toggle">
                    <i class="fa fa-angle-down"></i>
                </button>
            </div>
        </div>
        <div class="panel-body"
             style="display:none;max-height:500px;overflow:auto;">
            <%include file="dryad_citation.mako"/>
        </div>
    </div>
</div>
