from __future__ import annotations

import types
import sys
from pathlib import Path

import pytest

from tools.resume_parse import convert_pdf_to_markdown


@pytest.fixture()
def fake_pdf(tmp_path: Path) -> Path:
    p = tmp_path / "sample.pdf"
    p.write_bytes(b"%PDF-1.4\n% minimal test pdf placeholder\n")
    return p


def install_fake_markitdown(return_value):
    class FakeMarkItDown:
        def convert(self, path: str):  # noqa: ARG002 - simulated API
            return return_value

    fake_module = types.SimpleNamespace(MarkItDown=FakeMarkItDown)
    sys.modules["markitdown"] = fake_module


def uninstall_fake_markitdown():
    sys.modules.pop("markitdown", None)


def test_returns_empty_on_none():
    assert convert_pdf_to_markdown(None) == ""


def test_returns_empty_on_missing_file(tmp_path: Path):
    missing = tmp_path / "nope.pdf"
    assert convert_pdf_to_markdown(str(missing)) == ""


def test_returns_empty_on_non_pdf(tmp_path: Path):
    p = tmp_path / "file.txt"
    p.write_text("hello", encoding="utf-8")
    assert convert_pdf_to_markdown(str(p)) == ""


def test_markitdown_not_installed_returns_empty(fake_pdf: Path):
    uninstall_fake_markitdown()
    # Ensure import fails
    if "markitdown" in sys.modules:
        del sys.modules["markitdown"]
    assert convert_pdf_to_markdown(str(fake_pdf)) == ""


def test_markitdown_string_result(fake_pdf: Path):
    uninstall_fake_markitdown()
    install_fake_markitdown("Hello MD")
    try:
        assert convert_pdf_to_markdown(str(fake_pdf)) == "Hello MD"
    finally:
        uninstall_fake_markitdown()


def test_markitdown_dict_result(fake_pdf: Path):
    uninstall_fake_markitdown()
    install_fake_markitdown({"text_content": "From dict"})
    try:
        assert convert_pdf_to_markdown(str(fake_pdf)) == "From dict"
    finally:
        uninstall_fake_markitdown()


def test_markitdown_list_result(fake_pdf: Path):
    uninstall_fake_markitdown()
    install_fake_markitdown([{"markdown": "From list"}])
    try:
        assert convert_pdf_to_markdown(str(fake_pdf)) == "From list"
    finally:
        uninstall_fake_markitdown()


def test_markitdown_raises_returns_empty(fake_pdf: Path):
    class RaisingMID:
        def convert(self, path: str):  # noqa: ARG002
            raise RuntimeError("boom")

    sys.modules["markitdown"] = types.SimpleNamespace(MarkItDown=RaisingMID)
    try:
        assert convert_pdf_to_markdown(str(fake_pdf)) == ""
    finally:
        uninstall_fake_markitdown()
