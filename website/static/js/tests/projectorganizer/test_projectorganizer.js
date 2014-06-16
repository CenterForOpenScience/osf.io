describe("Jasmine works at all", function () {
    beforeEach(function () {
        jasmine.Ajax.install();
    });

    afterEach(function () {
        jasmine.Ajax.uninstall();
    });

    it("true equals true", function () {
        expect(true).toBe(true);
    });

    it("ajax specifying response when you need it", function () {
        var doneFn = jasmine.createSpy("success");

        var xhr = new XMLHttpRequest();
        xhr.onreadystatechange = function (arguments) {
            if (this.readyState == this.DONE) {
                doneFn(this.responseText);
            }
        };
        xhr.open("GET", "/some/cool/url");
        xhr.send();
        expect(jasmine.Ajax.requests.mostRecent().url).toBe('/some/cool/url');
        expect(doneFn).not.toHaveBeenCalled();
        jasmine.Ajax.requests.mostRecent().response({
            "status": 200,
            "contentType": 'text/plain',
            "responseText": 'awesome response'
        });
        expect(doneFn).toHaveBeenCalledWith('awesome response');
    });
});

describe("Dahsboard has a project organizer", function () {
    beforeEach(function (done) {
        var projectbrowser = new ProjectOrganizer('#project-grid');
    });

    it("appears on the dashboard", function () {

            expect($('#project-grid').html()).not.toEqual('');

    });
});
