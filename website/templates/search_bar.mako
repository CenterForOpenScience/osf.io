<div class="osf-search" data-bind="fadeVisible: showSearch" style="display: none">
    <div class="container">
        <div class="row">
            <div class="col-md-12">
                <form class="input-group" data-bind="submit: submit">
                    <input id="searchPageFullBar" name="search-placeholder" type="text" class="osf-search-input form-control" placeholder="Search" data-bind="value: query, hasFocus: true">
                    <label id="searchBarLabel" class="search-label-placeholder" for="search-placeholder">Search</label>
                    <span class="input-group-btn">
                        <button type=button class="btn osf-search-btn" data-bind="click: submit"><i class="fa fa-circle-arrow-right fa-lg"></i></button>
                        <button type=button class="btn osf-search-btn" data-bind="click: help"><i class="fa fa-question fa-lg"></i></button>
                        <button type="button" class="btn osf-search-btn" data-bind="visible: showClose, click : toggleSearch"><i class="fa fa-times fa-lg"></i></button>
                    </span>
                </form>
            </div>
        </div>
    </div>
</div>

