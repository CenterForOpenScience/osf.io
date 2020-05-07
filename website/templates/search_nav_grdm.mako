                        <div>
                            <ul class="pager">
                                <li data-bind="css: {disabled: !prevPageExists()}">
                                    <a href="#" data-bind="click: pagePrev">Previous Page </a>
                                </li>
                                <!-- ko if: totalPages() < pagesShown() -->
                                    <!-- ko foreach: listIndices() -->
                                    <span data-bind="css: {disabled: $parent.isCurrentPage($data)}">
                                        <a data-bind="click: $parent.pageNth, text: $data"></a>
                                    </span>
                                    <!-- /ko -->
                                <!-- /ko -->
                                <!-- ko if: ((totalPages() > pagesShown()) && (currentPage() <= center)) -->
                                    <!-- ko foreach: listIndices() -->
                                    <span data-bind="css: {disabled: $parent.isCurrentPage($data)}">
                                        <a data-bind="click: $parent.pageNth, text: $data"></a>
                                    </span>
                                    <!-- /ko -->
                                    <span>
                                    ...
                                    </span>
                                    <span>
                                        <a data-bind="click: pageLast, text: totalPages()"></a>
                                    </span>
                                <!-- /ko -->
                                <!-- ko if: ((totalPages() > pagesShown()) && (currentPage() > center) && ((listIndices().slice(-1)[0] + 1) < totalPages())) -->
                                    <span>
                                        <a data-bind="click: pageFirst, text: 1"></a>
                                    </span>
                                    <span>
                                    ...
                                    </span>
                                    <!-- ko foreach: listIndices() -->
                                    <span data-bind="css: {disabled: $parent.isCurrentPage($data)}">
                                        <a data-bind="click: $parent.pageNth, text: $data"></a>
                                    </span>
                                    <!-- /ko -->
                                    <span>
                                    ...
                                    </span>
                                    <span data-bind="css: {disabled: isCurrentPage(totalPages())}">
                                        <a data-bind="click: pageLast, text: totalPages()"></a>
                                    </span>
                                <!-- /ko -->
                                <!-- ko if: ((totalPages() > pagesShown()) && (currentPage() > center) && ((listIndices().slice(-1)[0] + 1) >= totalPages())) -->
                                    <span>
                                        <a data-bind="click: pageFirst, text: 1"></a>
                                    </span>
                                    <span>
                                    ...
                                    </span>
                                    <!-- ko foreach: listIndices() -->
                                    <span data-bind="css: {disabled: $parent.isCurrentPage($data)}">
                                        <a data-bind="click: $parent.pageNth, text: $data"></a>
                                    </span>
                                    <!-- /ko -->
                                <!-- /ko -->
                                <li data-bind="css: {disabled: !nextPageExists()}">
                                    <a href="#" data-bind="click: pageNext"> Next Page</a>
                                </li>
                            </ul>
                            <center>
                                <form data-bind="submit: pageNthByUser">
                                    Page
                                    <input type="tel" style="width: 50px;" data-bind="value: currentPage"/>
                                    <button data-bind="visible: false" type="submit"></button>
                                    /
                                    <span data-bind="text: totalPages()"></span>
                                </form>
                            </center>
                            <br>
                        </div>
