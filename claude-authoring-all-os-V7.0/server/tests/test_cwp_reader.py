"""Tests for richer .cwp / .cvw extraction — manifest, inventory, outline.

Unit tests run against hand-crafted byte fixtures (no external files needed).
Real-sample smoke tests are skipped when the sample .cwp files aren't present.
"""

from __future__ import annotations

import struct
import zipfile
from io import BytesIO
from pathlib import Path

import pytest

from caseware_authoring_tools.cwp_reader.cwp_reader import (
    CwpReader,
    _categorize_inner_file,
    _parse_bookmark_records,
    _parse_paragraph_index,
    _parse_section_index,
)


# === Unit tests: binary parsers ===


def _bookmark_record(name: str, label: str | None = None, meta: tuple[int, ...] = (0, 0, 0, 0)) -> bytes:
    label = label or name
    return (
        struct.pack("<H", len(name)) + name.encode("ascii")
        + struct.pack("<H", len(label)) + label.encode("ascii")
        + struct.pack("<4I", *meta)
    )


def test_bookmark_parser_single_record() -> None:
    data = struct.pack("<3I", 1, 1, 2) + _bookmark_record("EBP DCP Engagement Letter")
    records, warnings = _parse_bookmark_records(data)
    assert warnings == []
    assert len(records) == 1
    assert records[0]["name"] == "EBP DCP Engagement Letter"
    assert records[0]["meta"] == [0, 0, 0, 0]


def test_bookmark_parser_multiple_records() -> None:
    data = (
        struct.pack("<3I", 1, 3, 2)
        + _bookmark_record("FLATFORM_GUIDANCE")
        + _bookmark_record("COVER_PAGE", meta=(1, 5, 1, 3))
        + _bookmark_record("TOC_INTRO")
    )
    records, warnings = _parse_bookmark_records(data)
    assert warnings == []
    assert [r["name"] for r in records] == ["FLATFORM_GUIDANCE", "COVER_PAGE", "TOC_INTRO"]
    assert records[1]["meta"] == [1, 5, 1, 3]


def test_bookmark_parser_stops_on_trailing_junk() -> None:
    data = (
        struct.pack("<3I", 1, 1, 2)
        + _bookmark_record("AO_HEADER")
        + b"\x00\x00\xff\xff"
    )
    records, warnings = _parse_bookmark_records(data)
    assert len(records) == 1
    assert any("trailing" in w for w in warnings)


def test_section_parser_roundtrip() -> None:
    data = (
        struct.pack("<3I", 0, 0xA1, 2)
        + struct.pack("<4I", 100, 10, 20, 0)
        + struct.pack("<4I", 200, 20, 30, 1)
    )
    records, warnings = _parse_section_index(data)
    assert warnings == []
    assert len(records) == 2
    assert records[0] == {"index": 0, "u32_0": 100, "u32_1": 10, "u32_2": 20, "u32_3": 0}


def test_paragraph_parser_roundtrip() -> None:
    offsets = [100, 200, 350, 400]
    data = struct.pack("<3I", 0, 0xA1, len(offsets)) + struct.pack(f"<{len(offsets)}I", *offsets)
    parsed, warnings = _parse_paragraph_index(data)
    assert parsed == offsets
    assert warnings == []


def test_paragraph_parser_non_monotonic_warns() -> None:
    offsets = [100, 50, 200]
    data = struct.pack("<3I", 0, 0xA1, len(offsets)) + struct.pack(f"<{len(offsets)}I", *offsets)
    _parsed, warnings = _parse_paragraph_index(data)
    assert any("monotonic" in w for w in warnings)


def test_categorize_inner_file() -> None:
    cases = [
        ("T.cvw", "caseview_template"),
        ("t.cvw.bak", "caseview_backup"),
        ("STYLE.sty", "style"),
        ("c.cgf", "style"),
        ("letter.docx", "embedded_document"),
        ("data.dbf", "database"),
        ("logo.bmp", "image"),
        ("something.weird", "other"),
    ]
    for filename, expected in cases:
        assert _categorize_inner_file(filename) == expected, filename


# === Synthetic .cwp fixture ===


def _build_synthetic_cwp() -> bytes:
    manifest_xml = (
        '<TemplatePackager xmlns="CWTemplatePackager">'
        '<OptionsData xmlns="">'
        '<PackagerVersion>8</PackagerVersion>'
        '<TemplateName>Synthetic</TemplateName>'
        '<GUID>00000000-0000-0000-0000-000000000001</GUID>'
        '<TemplateVersion><Major>1</Major><Minor>0</Minor><Build>0</Build><Tag/></TemplateVersion>'
        '<AllowPackage>1</AllowPackage>'
        '<Files><FolderName>Synthetic</FolderName>'
        '<File><FileName>SyntheticENGL.cvw</FileName><MD5>deadbeef</MD5></File>'
        '<File><FileName>MISSING.dbf</FileName><MD5>99999999</MD5></File>'
        '</Files>'
        '</OptionsData>'
        '</TemplatePackager>'
    )
    inner_buf = BytesIO()
    with zipfile.ZipFile(inner_buf, "w") as iz:
        iz.writestr("SyntheticENGL.cvw", b"NOT_A_REAL_OLE2_FILE")
        iz.writestr("EXTRA.txt", b"unmanifested")
    outer_buf = BytesIO()
    with zipfile.ZipFile(outer_buf, "w") as oz:
        oz.writestr("manifest.xml", manifest_xml)
        oz.writestr("OptionsData.cwp", inner_buf.getvalue())
    return outer_buf.getvalue()


@pytest.fixture
def synthetic_cwp(tmp_path: Path) -> Path:
    path = tmp_path / "synthetic.cwp"
    path.write_bytes(_build_synthetic_cwp())
    return path


def test_synthetic_manifest_and_inventory(synthetic_cwp: Path) -> None:
    with CwpReader(synthetic_cwp) as r:
        m = r.get_package_manifest()
        inv = r.get_file_inventory()
    assert m["files_folder"] == "Synthetic"
    present = {f["filename"]: f["present_in_inner_zip"] for f in m["files"]}
    assert present == {"SyntheticENGL.cvw": True, "MISSING.dbf": False}
    assert m["raw"]["PackagerVersion"] == "8"
    assert inv["manifest_only"] == ["MISSING.dbf"]
    assert inv["zip_only"] == ["EXTRA.txt"]


# === Real-sample smoke tests ===


_SAMPLES = {
    "frazier": Path("C:/Users/jason/OneDrive/Documents/Frazier-Deeter.cwp"),
    "bt": Path("C:/Users/jason/Downloads/BT Examinations ver 2.01 9-29-25 1155pm - FINAL.cwp"),
}


@pytest.mark.skipif(not _SAMPLES["frazier"].exists(), reason="Frazier sample not present")
def test_real_frazier_engl() -> None:
    with CwpReader(_SAMPLES["frazier"]) as r:
        o = r.get_document_outline("ENGL")
    assert o["bookmarks"][0]["name"] == "EBP DCP Engagement Letter"
    assert o["section_count"] == 96
    assert o["paragraphs"] == sorted(o["paragraphs"])


@pytest.mark.skipif(not _SAMPLES["bt"].exists(), reason="BT Examinations sample not present")
def test_real_bt_full_sweep() -> None:
    """Every BT template parses without raising; paragraphs monotonic."""
    with CwpReader(_SAMPLES["bt"]) as r:
        for tmpl in r.list_templates():
            o = r.get_document_outline(tmpl["code"])
            if o["paragraphs"]:
                assert o["paragraphs"] == sorted(o["paragraphs"])
