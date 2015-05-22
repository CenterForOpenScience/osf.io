<div class="osf-search" data-bind="fadeVisible: showSearch" style="display: none">
    <div class="container">
        <div class="row">
            <div class="col-md-12">
                <form class="input-group" data-bind="submit: submit">
                    <input id="searchPageFullBar" name="search-placeholder" type="text" class="osf-search-input form-control" data-bind="value: query, hasFocus: true">
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

<script>
/** Only for Search Bar Placeholder -- Allow IE and other browsers to work as the same */
function placeholder(inputDom, inputLabel) {
    inputDom.on('input', function () {
        if (inputDom.val() === '') {
            inputLabel.css( "visibility", "visible" );
        } else {
            inputLabel.css( "visibility", "hidden" );
        }
    });
}
$(document).ready(function() {
    var inputDom =  $("#searchPageFullBar");
    var inputLabel =  $('#searchBarLabel');
    placeholder(inputDom, inputLabel);
    inputDom.focus();

    //Make sure IE cursor is located at the end of text
    var $inputVal = inputDom.val();
    inputDom.val('').val($inputVal);

    //For search page with existing input, make sure placeholder is hidden.
    if(inputDom.val() !== '' ){
         inputLabel.css( "visibility", "hidden" );
    }
});
</script>
