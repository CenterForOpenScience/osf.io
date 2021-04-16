<!-- for widget -->

<div id="${addon_short_name}Scope" class="scripted">
    <h4 class="addon-title">
        <img class="addon-icon" src=${addon_icon_url}>
        ${addon_full_name}
    </h4>
    <!-- Settings Pane -->
    <div class="${addon_short_name}-settings">
        <div class="row">
            <div class="col-md-12">
                BinderHub URL:
                <a
                  data-bind="attr: {href: binderUrl}, text: binderUrl" target="_blank"
                  rel="noopener"
                ></a>
            </div>
        </div>
        <!-- end row -->
    </div>
</div>
