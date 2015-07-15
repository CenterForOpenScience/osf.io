<div class="row" data-bind="attr: {id: $index}, event: {mouseover: $parent.highlightRow, mouseout: $parent.unhighlightRow, click: $parent.goToDraft}">
    <div data-bind="text: $data.registration_metadata.q1.value" class="col-md-1" id="submission_title"></div>
    <div data-bind="text: $data.initiator.fullname" class="col-md-1" id="name"></div>
    <div data-bind="text: $data.initiator.username" class="col-md-1" id="email"></div>
    <div data-bind="text: $parent.formatTime($data.initiated)" class="col-md-1" id="begun"></div>
    <div data-bind="text: $parent.formatTime($data.updated)" class="col-md-1" id="submitted"></div>
    <!-- comments sent -->
    <div  class="col-md-1" id="comments_sent">
        <span data-bind="text: $parent.commentsSent, attr: {class: 'comments_sent' + $index()}"></span><i data-bind="click: $parent.editItem.bind($data, 'comments_sent' + $index()), clickBubble: false, event: {mouseover: $parent.enlargeIcon, mouseout: $parent.shrinkIcon}, attr: {class: 'comments_sent' + $index() + ' fa fa-pencil'}" style="margin-left: 10px"></i>
        <div data-bind="attr: {class: 'input_comments_sent' + $index()}, valueUpdate: 'afterkeydown', enterkey: $parent.stopEditing.bind($data, 'comments_sent' + $index())" style="display: none">
            <div><input type="radio" data-bind="value: 'no', attr: {class: 'input_comments_sent' + $index()}, checked: $parent.commentsSent"/>No</div>
            <div><input type="radio" data-bind="value: 'yes', attr: {class: 'input_comments_sent' + $index()}"/>Yes</div>
        </div>
    </div>
    <div data-bind="text: 'no'" class="col-md-1" id="new_comments"></div>
    <div data-bind="text: $data.flags.isApproved" class="col-md-1" id="approved"></div>
    <div data-bind="text: 'no'" class="col-md-1" id="registered"></div>
    <!-- proof of publication -->
    <div class="col-md-1" id="proof_of_pub">
        <span data-bind="text: $parent.proofOfPub, attr: {class: 'proof_of_pub' + $index()}"></span><i data-bind="click: $parent.editItem.bind($data, 'proof_of_pub' + $index()), clickBubble: false, event: {mouseover: $parent.enlargeIcon, mouseout: $parent.shrinkIcon}, attr: {class: 'proof_of_pub' + $index() + ' fa fa-pencil'}" style="margin-left: 10px"></i>
        <div data-bind="attr: {class: 'input_proof_of_pub' + $index()}, valueUpdate: 'afterkeydown', enterkey: $parent.stopEditing.bind($data, 'proof_of_pub' + $index())" style="display: none">
            <div><input type="radio" data-bind="value: 'no', attr: {class: 'input_proof_of_pub' + $index()}, checked: $parent.proofOfPub"/>No</div>
            <div><input type="radio" data-bind="value: 'yes', attr: {class: 'input_proof_of_pub' + $index()}"/>Yes</div>
        </div>
    </div>
    <!-- payment sent -->
    <div class="col-md-1" id="paymentSent">
        <span data-bind="text: $data.flags.paymentSent, attr: {class: 'paymentSent' + $index()}"></span><i data-bind="click: $parent.editItem.bind($data, 'paymentSent' + $index()), clickBubble: false, event: {mouseover: $parent.enlargeIcon, mouseout: $parent.shrinkIcon}, attr: {class: 'paymentSent' + $index() + ' fa fa-pencil'}" style="margin-left: 10px"></i>
        <div data-bind="attr: {class: 'input_paymentSent' + $index()}, valueUpdate: 'afterkeydown', enterkey: $parent.stopEditing.bind($data, 'paymentSent' + $index())" style="display: none">
            <div><input type="radio" data-bind="attr: {class: 'input_paymentSent' + $index(), name: 'input_paymentSent' + $index()}, checked: $parent.paymentSent, checkedValue: true"/>True</div>
            <div><input type="radio" data-bind="attr: {class: 'input_paymentSent' + $index(), name: 'input_paymentSent' + $index()}, checked: $parent.paymentSent, checkedValue: false"/>False</div>
        </div>
    </div>
    <!-- notes -->
    <div class="col-md-1" id="notes">
        <span data-bind="text: $parent.notes, attr: {class: 'notes' + $index()}"></span><i data-bind="click: $parent.editItem.bind($data, 'notes' + $index()), clickBubble: false, event: {mouseover: $parent.enlargeIcon, mouseout: $parent.shrinkIcon}, attr: {class: 'notes' + $index() + ' fa fa-pencil'}" style="margin-left: 10px"></i>
        <div data-bind="attr: {class: 'input_notes' + $index()}, valueUpdate: 'afterkeydown', enterkey: $parent.stopEditing.bind($data, 'notes' + $index())" style="display: none">
            <div><input type="text" data-bind="value: $parent.notes, attr: {class: 'input_notes' + $index()}"/></div>
        </div>
    </div>
</div>
