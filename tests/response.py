from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag
from werkzeug import Request
from werkzeug.datastructures import Headers
from werkzeug.test import TestResponse, Client
from typing import Any
from collections.abc import Iterable


@dataclass(kw_only=True, slots=True)
class Form:
    values: dict[str, Any]
    method: str
    request: Request
    action_path: str = None

    @classmethod
    def from_html(cls, request: Request, html: Tag) -> 'Form':
        return cls(
            request=request,
            method=html.attrs.get('method'),
            values={
                item.attrs.get('name'): item.attrs.get('value') for item in html.find_all('input')
            },
            action_path=html.attrs.get('action', request.path)
        )

    def __setitem__(self, key: str, value: Any) -> None:
        self.values[key] = value

    def __getitem__(self, item: str) -> Any:
        return self.values[item]

    def submit(self, client: Client, **kwargs):
        return client.open(
            self.action_path,
            method=self.method.upper(),
            data=self.values,
            headers={**self.request.headers},
            **kwargs,
        )


class FormsTestResponse(TestResponse):

    def __init__(
            self,
            response: Iterable[bytes],
            status: str,
            headers: Headers,
            request: Request,
            history: tuple[TestResponse] = (),  # type: ignore
            **kwargs: Any,
    ):
        super().__init__(response, status, headers, request, history, **kwargs)
        self._html: BeautifulSoup | None = None

    @property
    def html(self) -> BeautifulSoup:
        if self._html:
            return self._html
        if 'html' not in self.content_type:
            raise AttributeError(f'Not an HTML response body (content-type: {self.content_type})')
        self._html = BeautifulSoup(self.text, 'html.parser')
        return self._html

    def get_form(self, form_name: str):
        return Form.from_html(self.request, self.html.find(id=form_name))
