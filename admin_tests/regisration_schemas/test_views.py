import pytest

from django.test import RequestFactory

from osf.models import RegistrationSchema
from admin_tests.utilities import setup_view
from admin.registration_schemas import views
from django.contrib.messages.storage.fallback import FallbackStorage

from django.core.files.uploadedfile import SimpleUploadedFile
from osf_tests.factories import (
    RegistrationProviderFactory,
    RegistrationFactory,
)


@pytest.mark.django_db
class TestRegistrationSchemaList:
    @pytest.fixture()
    def req(self):
        req = RequestFactory().get("/fake_path")
        # django.contrib.messages has a bug which effects unittests
        # more info here -> https://code.djangoproject.com/ticket/17971
        setattr(req, "session", "session")
        messages = FallbackStorage(req)
        setattr(req, "_messages", messages)
        return req

    @pytest.fixture()
    def registration_schema(self):
        return RegistrationSchema.objects.create(
            name="foo",
            schema={"foo": 42, "atomicSchema": True},
            schema_version=1,
            active=False,
            visible=False,
        )

    @pytest.fixture()
    def view(self, req, registration_schema):
        view = views.RegistrationSchemaListView()
        view.kwargs = {"registration_schema_id": registration_schema.id}
        return setup_view(view, req)

    def test_registration_schema_list(self, view, registration_schema, req):
        data = view.get_context_data()
        assert any(
            item.id == registration_schema.id
            for item in data["registration_schemas"]
        )


@pytest.mark.django_db
@pytest.mark.urls("admin.base.urls")
class TestRegistrationSchemaDetail:
    @pytest.fixture()
    def req(self):
        req = RequestFactory().get("/fake_path")
        # django.contrib.messages has a bug which effects unittests
        # more info here -> https://code.djangoproject.com/ticket/17971
        setattr(req, "session", "session")
        messages = FallbackStorage(req)
        setattr(req, "_messages", messages)
        return req

    @pytest.fixture()
    def registration_schema(self):
        return RegistrationSchema.objects.create(
            name="foo",
            schema={"foo": 42, "atomicSchema": True},
            schema_version=1,
            active=False,
            visible=False,
        )

    @pytest.fixture()
    def view(self, req, registration_schema):
        plain_view = views.RegistrationSchemaDetailView()
        view = setup_view(plain_view, req)
        view.kwargs = {"registration_schema_id": registration_schema.id}
        return view

    def test_registration_schema_detail(self, view, registration_schema):
        registration_schema.visible = True
        registration_schema.active = True
        registration_schema.save()

        context = view.get_context_data()
        assert context["registration_schema"] == registration_schema
        assert context["form"].data["active"] == registration_schema.active
        assert context["form"].data["visible"] == registration_schema.visible

    def test_registration_schema_update(self, view, registration_schema):
        assert not registration_schema.visible
        assert not registration_schema.active
        form = view.get_form()

        # `['on'] indicates a selected toggle from this form
        form.data["active"] = ["on"]
        form.data["visible"] = ["on"]

        view.form_valid(form)

        registration_schema.refresh_from_db()
        assert registration_schema.visible
        assert registration_schema.active


@pytest.mark.django_db
@pytest.mark.urls("admin.base.urls")
class TestCreateRegistrationSchema:
    @pytest.fixture()
    def req(self):
        req = RequestFactory().get("/fake_path")
        # django.contrib.messages has a bug which effects unittests
        # more info here -> https://code.djangoproject.com/ticket/17971
        setattr(req, "session", "session")
        messages = FallbackStorage(req)
        setattr(req, "_messages", messages)
        return req

    @pytest.fixture
    def csv_data(self):
        return (
            b"block_type,display_text,help_text,example_text,required,registration_response_key,NOEX_updates,"
            b'NOEX_update_reason\npage-heading,This is the page heading,"This is extra, helpful context",,FALSE,,'
            b"FALSE,"
        )

    @pytest.fixture
    def csv_file(self, csv_data):
        return SimpleUploadedFile(
            "test_file.csv", csv_data, content_type="application/csv"
        )

    @pytest.fixture()
    def view(self, req):
        plain_view = views.RegistrationSchemaCreateView()
        view = setup_view(plain_view, req)
        return view

    @pytest.fixture()
    def form(self, view, csv_file):
        form = view.get_form()
        form.data["name"] = "Trust the Process"
        form.files["schema"] = csv_file
        return form

    def test_registration_schema_create(self, view, csv_file, form, req):
        view.form_valid(form)
        registration_schema = RegistrationSchema.objects.get(
            name=form.data["name"]
        )
        assert registration_schema.schema_blocks.count() == 1
        block = registration_schema.schema_blocks.first()
        assert block.block_type == "page-heading"
        assert block.display_text == "This is the page heading"
        assert registration_schema.schema_version == 1

    def test_registration_schema_increment_version(
        self, view, csv_file, form, req
    ):
        view.form_valid(form)
        registration_schema = RegistrationSchema.objects.get_latest_version(
            name=form.data["name"]
        )
        assert registration_schema.schema_version == 1

        view.form_valid(form)
        registration_schema = RegistrationSchema.objects.get_latest_version(
            name=form.data["name"]
        )
        assert registration_schema.schema_version == 2

    def test_registration_schema_csv_to_blocks(self, view, csv_file):
        blocks = view.csv_to_blocks(csv_file)
        assert len(blocks) == 1
        assert blocks[0]["block_type"] == "page-heading"
        assert blocks[0]["display_text"] == "This is the page heading"


@pytest.mark.django_db
@pytest.mark.urls("admin.base.urls")
class TestDeleteRegistrationSchema:
    @pytest.fixture()
    def req(self):
        req = RequestFactory().get("/fake_path")
        # django.contrib.messages has a bug which effects unittests
        # more info here -> https://code.djangoproject.com/ticket/17971
        setattr(req, "session", "session")
        messages = FallbackStorage(req)
        setattr(req, "_messages", messages)
        return req

    @pytest.fixture()
    def registration_schema(self):
        return RegistrationSchema.objects.create(
            name="foo",
            schema={"foo": 42, "atomicSchema": True},
            schema_version=1,
            active=False,
            visible=False,
        )

    @pytest.fixture()
    def registration(self, registration_schema):
        registration = RegistrationFactory()
        registration.registered_schema.add(registration_schema)
        registration.save()
        return registration

    @pytest.fixture()
    def provider(self, registration_schema):
        provider = RegistrationProviderFactory()
        registration_schema.providers.add(provider)
        return provider

    @pytest.fixture()
    def view(self, req, registration_schema):
        view = views.RegistrationSchemaDeleteView()
        view = setup_view(view, req)
        view.kwargs = {"registration_schema_id": registration_schema.id}
        return view

    def test_registration_schema_delete(self, req, view, registration_schema):
        view.delete(req)
        assert not RegistrationSchema.objects.filter(id=registration_schema.id)

    def test_registration_schema_prevent_delete_if_used(
        self, req, view, registration_schema, provider, registration
    ):
        """
        If a Registration Schema is being used as part of registration it shouldn't be deletable from the admin app.
        """
        view.delete(req)
        assert RegistrationSchema.objects.filter(id=registration_schema.id)
