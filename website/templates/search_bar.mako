<div class="osf-search" data-bind="fadeVisible: showSearch" style="display: none">
    <div class="container">
        <div class="row">
            <div class="col-md-12">
                <form class="input-group" data-bind="submit: submit">
                    <input id="searchPageFullBar" type="text" class="osf-search-input form-control" placeholder="Search" data-bind="value: query, hasFocus: true">
                    <span class="input-group-btn">
                        <button type=button class="btn osf-search-btn" data-bind="click: submit"><i class="icon-circle-arrow-right icon-lg"></i></button>
                        <button type=button class="btn osf-search-btn" data-bind="click: help"><i class="icon-question icon-lg"></i></button>
                        <button type="button" class="btn osf-search-btn" data-bind="visible: showClose, click : toggleSearch"><i class="icon-remove icon-lg"></i></button>
                    </span>
                </form>
            </div>
        </div>
    </div>
</div>
