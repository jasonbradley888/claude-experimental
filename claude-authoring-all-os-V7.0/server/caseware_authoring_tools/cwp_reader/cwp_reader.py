"""Offline CaseView template package reader — no COM/Windows dependency.

Parses .cwp template packages to extract template structure and cell/field
inventories using only file-based parsing (ZIP, XML, OLE2).

Works on Mac, Linux, and Windows.
"""

from __future__ import annotations

import io
import re
import struct
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class PackageInfo:
    """Metadata from a .cwp manifest."""

    template_name: str
    guid: str
    version: str
    source_path: str
    file_count: int
    cvw_count: int


@dataclass
class TemplateInfo:
    """Metadata about a single .cvw template file."""

    filename: str
    code: str
    file_size: int
    cell_names: list[str] = field(default_factory=list)
    bookmarks: list[str] = field(default_factory=list)
    stream_sizes: dict[str, int] = field(default_factory=dict)


class CwpReader:
    """Reads and parses .cwp template packages.

    Usage::

        with CwpReader("path/to/template.cwp") as reader:
            info = reader.get_package_info()
            templates = reader.list_templates()
            cells = reader.get_template_cells("ENGL")
    """

    def __init__(self, cwp_path: str | Path) -> None:
        self._path = Path(cwp_path)
        if not self._path.exists():
            raise FileNotFoundError(f"File not found: {self._path}")
        if not self._path.suffix.lower() == ".cwp":
            raise ValueError(f"Expected .cwp file, got: {self._path.suffix}")

        self._outer_zip = zipfile.ZipFile(self._path, "r")
        inner_data = self._outer_zip.read("OptionsData.cwp")
        self._inner_zip = zipfile.ZipFile(io.BytesIO(inner_data), "r")

        # Parse manifest for template name prefix
        raw = self._outer_zip.read("manifest.xml")
        # Some CaseWare manifests contain Windows-1252 bytes (e.g., 0xa7 §)
        # despite declaring UTF-8; fall back to latin-1 which never fails.
        try:
            self._manifest_xml = raw.decode("utf-8")
        except UnicodeDecodeError:
            self._manifest_xml = raw.decode("latin-1")
        self._template_name = self._parse_template_name()

    def __enter__(self) -> CwpReader:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def close(self) -> None:
        """Close ZIP handles."""
        self._inner_zip.close()
        self._outer_zip.close()

    def _parse_template_name(self) -> str:
        """Extract template name from manifest.xml."""
        # Strip namespace for easier parsing
        xml_clean = re.sub(r'\s+xmlns="[^"]*"', "", self._manifest_xml, count=2)
        try:
            root = ET.fromstring(xml_clean)
            name_elem = root.find(".//TemplateName")
            if name_elem is not None and name_elem.text:
                return name_elem.text
        except ET.ParseError:
            pass
        # Fallback: derive from filename
        return self._path.stem

    def get_package_info(self) -> dict[str, Any]:
        """Parse manifest.xml and return package metadata."""
        xml_clean = re.sub(r'\s+xmlns="[^"]*"', "", self._manifest_xml, count=2)
        info: dict[str, Any] = {
            "template_name": self._template_name,
            "guid": "",
            "version": "",
            "source_path": "",
            "file_count": 0,
            "cvw_count": 0,
        }

        try:
            root = ET.fromstring(xml_clean)
            guid = root.find(".//GUID")
            if guid is not None and guid.text:
                info["guid"] = guid.text

            major = root.find(".//TemplateVersion/Major")
            minor = root.find(".//TemplateVersion/Minor")
            build = root.find(".//TemplateVersion/Build")
            parts = [
                major.text if major is not None and major.text else "0",
                minor.text if minor is not None and minor.text else "0",
                build.text if build is not None and build.text else "0",
            ]
            info["version"] = ".".join(parts)

            fname = root.find(".//FileName")
            if fname is not None and fname.text:
                info["source_path"] = fname.text

            files = root.findall(".//File")
            info["file_count"] = len(files)
        except ET.ParseError:
            pass

        # Count .cvw files in inner ZIP
        cvw_files = [n for n in self._inner_zip.namelist() if n.lower().endswith(".cvw")]
        info["cvw_count"] = len(cvw_files)

        return info

    def get_package_manifest(self) -> dict[str, Any]:
        """Return the complete manifest.xml as a nested dict.

        Every element is surfaced (namespace stripped). Each ``<File>`` entry is
        returned with its ``FileName`` and ``MD5`` attributes, cross-referenced
        with the actual inner-zip contents via ``present_in_inner_zip``/
        ``inner_zip_size``.

        This is the richer counterpart to :meth:`get_package_info`, which only
        returns the 6 most common fields.

        Returns:
            Dict with keys:
              - ``raw``: every non-Files top-level element as ``{tag: value}``
              - ``files``: list of ``{filename, md5, folder, present_in_inner_zip, inner_zip_size}``
              - ``files_folder``: the ``<FolderName>`` from ``<Files>``, if any
              - ``parse_warnings``: list of strings describing any parse issues
        """
        warnings: list[str] = []
        xml_clean = re.sub(r'\s+xmlns="[^"]*"', "", self._manifest_xml, count=2)
        raw: dict[str, Any] = {}
        files: list[dict[str, Any]] = []
        folder = ""

        try:
            root = ET.fromstring(xml_clean)
            # Walk OptionsData (or root) and collect every element
            container = root.find("OptionsData")
            if container is None:
                container = root

            # Inner-zip size lookup
            inner_sizes = {
                info.filename: info.file_size for info in self._inner_zip.infolist()
            }

            for child in container:
                if child.tag == "Files":
                    fn = child.find("FolderName")
                    if fn is not None and fn.text:
                        folder = fn.text
                    for f in child.findall("File"):
                        filename_elem = f.find("FileName")
                        md5_elem = f.find("MD5")
                        filename = (
                            filename_elem.text
                            if filename_elem is not None and filename_elem.text
                            else ""
                        )
                        md5 = (
                            md5_elem.text
                            if md5_elem is not None and md5_elem.text
                            else ""
                        )
                        files.append(
                            {
                                "filename": filename,
                                "md5": md5,
                                "folder": folder,
                                "present_in_inner_zip": filename in inner_sizes,
                                "inner_zip_size": inner_sizes.get(filename),
                            }
                        )
                else:
                    raw[child.tag] = _element_to_dict(child)
        except ET.ParseError as e:
            warnings.append(f"ET.ParseError: {e}")

        result: dict[str, Any] = {
            "raw": raw,
            "files": files,
            "files_folder": folder,
        }
        if warnings:
            result["parse_warnings"] = warnings
        return result

    def get_file_inventory(self) -> dict[str, Any]:
        """Enumerate every file in the inner zip, grouped by category.

        Unlike :meth:`list_templates` (which filters to ``.cvw`` only), this
        surfaces all 15+ file types inside ``OptionsData.cwp`` — styles,
        configs, embedded docx/xlsx, dBASE tables, images, etc.

        Also cross-references against the manifest's ``<File>`` list to report
        drift (files in manifest but not in zip, or vice versa).

        Returns:
            Dict with keys:
              - ``total_files``: int
              - ``by_category``: dict[category, list of {filename, size, extension}]
              - ``by_extension``: dict[ext, count]
              - ``manifest_only``: list[str] — manifest files not in inner zip
              - ``zip_only``: list[str] — inner-zip files not in manifest
        """
        inner_files = {info.filename: info.file_size for info in self._inner_zip.infolist()}

        by_category: dict[str, list[dict[str, Any]]] = {}
        by_extension: dict[str, int] = {}
        for name, size in inner_files.items():
            category = _categorize_inner_file(name)
            ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
            by_extension[ext] = by_extension.get(ext, 0) + 1
            by_category.setdefault(category, []).append(
                {"filename": name, "size": size, "extension": ext}
            )
        for category in by_category:
            by_category[category].sort(key=lambda d: str(d["filename"]))

        # Cross-reference manifest
        manifest = self.get_package_manifest()
        manifest_names = {f["filename"] for f in manifest["files"] if f["filename"]}
        zip_names = set(inner_files.keys())
        manifest_only = sorted(manifest_names - zip_names)
        zip_only = sorted(zip_names - manifest_names)

        return {
            "total_files": len(inner_files),
            "by_category": by_category,
            "by_extension": dict(sorted(by_extension.items(), key=lambda x: -x[1])),
            "manifest_only": manifest_only,
            "zip_only": zip_only,
        }

    def _code_from_filename(self, filename: str) -> str:
        """Extract template code from a .cvw filename.

        E.g., 'EBP Defined Contribution Plan TemplateENGL.cvw' -> 'ENGL'
        """
        base = filename
        if base.lower().endswith(".cvw"):
            base = base[:-4]
        if base.lower().endswith(".bak"):
            base = base[:-4]

        # Strip the template name prefix
        prefix = self._template_name
        if base.startswith(prefix):
            return base[len(prefix):]

        # Fallback: return everything after the last known word
        return base

    def list_templates(self) -> list[dict[str, Any]]:
        """List all .cvw templates with codes and file sizes."""
        results = []
        for info in self._inner_zip.infolist():
            if info.filename.lower().endswith(".cvw") and not info.filename.lower().endswith(
                ".bak"
            ):
                code = self._code_from_filename(info.filename)
                results.append(
                    {
                        "code": code,
                        "filename": info.filename,
                        "file_size": info.file_size,
                    }
                )
        results.sort(key=lambda x: str(x["code"]))
        return results

    def get_template_cells(self, code: str) -> list[str]:
        """Get all cell/field names for a specific template.

        Requires olefile. Parses the Index/Cell OLE2 stream.

        Args:
            code: Template code (e.g., 'ENGL', 'FRAUD')

        Returns:
            Sorted list of cell name strings.
        """
        try:
            import olefile  # type: ignore[import-untyped]
        except ImportError:
            raise ImportError(
                "olefile is required for cell extraction. "
                "Install it with: pip install cwp-template-reader[olefile]"
            ) from None

        cvw_data = self._get_cvw_bytes(code)
        if cvw_data is None:
            raise FileNotFoundError(f"Template '{code}' not found in package")

        ole = olefile.OleFileIO(io.BytesIO(cvw_data))
        try:
            if not ole.exists("Index/Cell"):
                return []
            cell_data = ole.openstream("Index/Cell").read()
            return _parse_cell_names(cell_data)
        finally:
            ole.close()

    def get_all_cells(self) -> dict[str, list[str]]:
        """Get cell inventory for all templates.

        Returns:
            Dict mapping template code -> list of cell names.
        """
        result = {}
        for tmpl in self.list_templates():
            try:
                cells = self.get_template_cells(tmpl["code"])
                result[tmpl["code"]] = cells
            except (ImportError, FileNotFoundError):
                result[tmpl["code"]] = []
        return result

    def search_cells(self, pattern: str) -> list[dict[str, str]]:
        """Search for cells matching a regex pattern across all templates.

        Args:
            pattern: Regex pattern to match against cell names.

        Returns:
            List of dicts with 'code' and 'cell_name' keys.
        """
        compiled = re.compile(pattern, re.IGNORECASE)
        matches = []
        all_cells = self.get_all_cells()
        for code, cells in sorted(all_cells.items()):
            for cell in cells:
                if compiled.search(cell):
                    matches.append({"code": code, "cell_name": cell})
        return matches

    def get_template_structure(self, code: str) -> dict[str, Any]:
        """Get structural metadata for a specific template.

        Returns OLE2 stream sizes, bookmarks, and cell count.
        """
        try:
            import olefile
        except ImportError:
            raise ImportError(
                "olefile is required for template structure analysis. "
                "Install it with: pip install cwp-template-reader[olefile]"
            ) from None

        cvw_data = self._get_cvw_bytes(code)
        if cvw_data is None:
            raise FileNotFoundError(f"Template '{code}' not found in package")

        ole = olefile.OleFileIO(io.BytesIO(cvw_data))
        try:
            stream_sizes = {}
            for stream in ole.listdir():
                name = "/".join(stream)
                stream_sizes[name] = ole.get_size(name)

            bookmarks = []
            if ole.exists("Index/Bookmarks"):
                bm_data = ole.openstream("Index/Bookmarks").read()
                bookmarks = _parse_readable_strings(bm_data, min_len=4)

            cell_count = 0
            if ole.exists("Index/Cell"):
                cell_data = ole.openstream("Index/Cell").read()
                cell_count = len(_parse_cell_names(cell_data))

            return {
                "code": code,
                "stream_sizes": stream_sizes,
                "bookmarks": bookmarks,
                "cell_count": cell_count,
                "total_ole_size": sum(stream_sizes.values()),
            }
        finally:
            ole.close()

    def get_template_readable_content(self, code: str) -> dict[str, list[str]]:
        """Extract all readable strings from every OLE2 stream in a template.

        Useful for comprehensive content extraction — captures dynamic elements,
        labels, and text that may not appear in the cell index.

        Args:
            code: Template code (e.g., 'ENGL', 'FRAUD')

        Returns:
            Dict mapping stream name -> list of readable strings.
        """
        try:
            import olefile
        except ImportError:
            raise ImportError(
                "olefile is required for content extraction. "
                "Install it with: pip install cwp-template-reader[olefile]"
            ) from None

        cvw_data = self._get_cvw_bytes(code)
        if cvw_data is None:
            raise FileNotFoundError(f"Template '{code}' not found in package")

        ole = olefile.OleFileIO(io.BytesIO(cvw_data))
        try:
            content: dict[str, list[str]] = {}
            for stream in ole.listdir():
                name = "/".join(stream)
                try:
                    data = ole.openstream(name).read()
                    strings = _parse_readable_strings(data, min_len=3)
                    if strings:
                        content[name] = strings
                except Exception:
                    continue
            return content
        finally:
            ole.close()

    def get_document_outline(self, code: str) -> dict[str, Any]:
        """Return the structured document outline for a template.

        Parses three OLE2 streams:

        - ``Index/Bookmarks`` — length-prefixed ``(name, label, metadata)``
          records; parser returns ``[{name, label, meta: [u32×4]}]``.
        - ``Index/Sect`` — 12-byte header + 16-byte records (four u32s).
        - ``Index/Para`` — 12-byte header + u32 paragraph offsets.

        All parsers are defensive: malformed data is surfaced as
        ``parse_warning`` rather than raised.

        Args:
            code: Template code (e.g., ``'ENGL'``).

        Returns:
            Dict with ``bookmarks``, ``sections``, ``paragraphs`` keys.
        """
        try:
            import olefile
        except ImportError:
            raise ImportError(
                "olefile is required for document outline extraction. "
                "Install it with: pip install olefile"
            ) from None

        cvw_data = self._get_cvw_bytes(code)
        if cvw_data is None:
            raise FileNotFoundError(f"Template '{code}' not found in package")

        ole = olefile.OleFileIO(io.BytesIO(cvw_data))
        try:
            return _extract_outline(ole, code)
        finally:
            ole.close()

    def _get_cvw_bytes(self, code: str) -> bytes | None:
        """Find and read a .cvw file by template code."""
        code_upper = code.upper()
        for name in self._inner_zip.namelist():
            if not name.lower().endswith(".cvw"):
                continue
            file_code = self._code_from_filename(name)
            if file_code.upper() == code_upper:
                return self._inner_zip.read(name)
        return None


class CvwReader:
    """Reads a standalone .cvw CaseView template file (OLE2 compound document).

    Unlike CwpReader, this operates directly on a .cvw — no .cwp/ZIP wrapper.
    Shares the module-level _parse_cell_names() and _parse_readable_strings()
    helpers.

    Note: Standalone .cvw files may have encoded Index/Cell streams that
    the current parser cannot extract meaningful cell names from. Other
    streams (Form/Strings, Scripts, Index/Bookmarks) are fully readable.

    Usage::

        with CvwReader("path/to/template.cvw") as reader:
            structure = reader.get_structure()
            content = reader.get_readable_content()
    """

    def __init__(self, cvw_path: str | Path) -> None:
        self._path = Path(cvw_path)
        if not self._path.exists():
            raise FileNotFoundError(f"File not found: {self._path}")
        if not self._path.suffix.lower() == ".cvw":
            raise ValueError(f"Expected .cvw file, got: {self._path.suffix}")

        try:
            import olefile  # type: ignore[import-untyped]
        except ImportError:
            raise ImportError(
                "olefile is required for .cvw file reading. "
                "Install it with: pip install olefile"
            ) from None

        self._ole = olefile.OleFileIO(str(self._path))

    def __enter__(self) -> CvwReader:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def close(self) -> None:
        """Close the OLE2 file handle."""
        self._ole.close()

    def get_stream_sizes(self) -> dict[str, int]:
        """Return all OLE2 stream names with their sizes."""
        result: dict[str, int] = {}
        for stream in self._ole.listdir():
            name = "/".join(stream)
            result[name] = self._ole.get_size(name)
        return result

    def get_cells(self) -> list[str]:
        """Try to parse cell names from the Index/Cell stream.

        Returns an empty list if the stream is missing or if no valid cell
        names are extracted (likely encoded format in standalone .cvw files).
        """
        if not self._ole.exists("Index/Cell"):
            return []
        cell_data = self._ole.openstream("Index/Cell").read()
        return _parse_cell_names(cell_data)

    def get_bookmarks(self) -> list[str]:
        """Parse bookmark names from the Index/Bookmarks stream."""
        if not self._ole.exists("Index/Bookmarks"):
            return []
        bm_data = self._ole.openstream("Index/Bookmarks").read()
        return _parse_readable_strings(bm_data, min_len=4)

    def get_readable_content(self) -> dict[str, list[str]]:
        """Extract readable ASCII strings from every OLE2 stream.

        For standalone .cvw files this is the primary extraction path —
        yields form labels, script content, style names, etc.

        Returns:
            Dict mapping stream name -> list of readable strings.
        """
        content: dict[str, list[str]] = {}
        for stream in self._ole.listdir():
            name = "/".join(stream)
            try:
                data = self._ole.openstream(name).read()
                strings = _parse_readable_strings(data, min_len=3)
                if strings:
                    content[name] = strings
            except Exception:
                continue
        return content

    def get_structure(self) -> dict[str, Any]:
        """Full structural metadata: streams, bookmarks, cell count."""
        stream_sizes = self.get_stream_sizes()
        return {
            "file_path": str(self._path),
            "file_size": self._path.stat().st_size,
            "stream_sizes": stream_sizes,
            "stream_count": len(stream_sizes),
            "total_ole_size": sum(stream_sizes.values()),
            "bookmarks": self.get_bookmarks(),
            "cell_count": len(self.get_cells()),
        }

    def get_document_outline(self) -> dict[str, Any]:
        """Return the structured document outline for this standalone .cvw.

        Mirror of :meth:`CwpReader.get_document_outline` — parses
        ``Index/Bookmarks`` (length-prefixed records), ``Index/Sect``
        (12-byte header + 16-byte records), and ``Index/Para`` (12-byte
        header + u32 offsets). Defensive: never raises on malformed data.
        """
        return _extract_outline(self._ole, code=self._path.stem)


def _parse_cell_names(cell_data: bytes) -> list[str]:
    """Parse cell names from an Index/Cell OLE2 stream.

    Cell names are ASCII strings separated by control characters (bytes < 32).
    We extract strings of 2+ printable chars and filter out pure numeric/offset values.
    """
    names: list[str] = []
    current: list[str] = []

    for byte in cell_data:
        if 32 <= byte < 127:
            current.append(chr(byte))
        else:
            if len(current) >= 2:
                name = "".join(current).strip()
                if name and not name.isdigit():
                    names.append(name)
            current = []

    # Flush remaining
    if len(current) >= 2:
        name = "".join(current).strip()
        if name and not name.isdigit():
            names.append(name)

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for n in names:
        if n not in seen:
            seen.add(n)
            unique.append(n)

    return sorted(unique)


def _parse_readable_strings(data: bytes, min_len: int = 4) -> list[str]:
    """Extract readable ASCII strings from binary data."""
    strings: list[str] = []
    current: list[str] = []

    for byte in data:
        if 32 <= byte < 127:
            current.append(chr(byte))
        else:
            if len(current) >= min_len:
                strings.append("".join(current).strip())
            current = []

    if len(current) >= min_len:
        strings.append("".join(current).strip())

    return strings


# === Richer extraction helpers (axes 1–3) ===


def _element_to_dict(elem: ET.Element) -> Any:
    """Convert an XML element to a nested dict/string.

    Leaf elements with text return the text. Elements with children return
    a dict. Mixed content is preserved by stuffing the text under ``"_text"``.
    Attributes are surfaced under ``"_attrs"`` when present.
    """
    children = list(elem)
    if not children:
        text = (elem.text or "").strip()
        if elem.attrib:
            return {"_text": text, "_attrs": dict(elem.attrib)}
        return text

    out: dict[str, Any] = {}
    if elem.attrib:
        out["_attrs"] = dict(elem.attrib)
    text = (elem.text or "").strip()
    if text:
        out["_text"] = text
    for child in children:
        value = _element_to_dict(child)
        if child.tag in out:
            existing = out[child.tag]
            if isinstance(existing, list):
                existing.append(value)
            else:
                out[child.tag] = [existing, value]
        else:
            out[child.tag] = value
    return out


def _categorize_inner_file(filename: str) -> str:
    """Categorize an inner-zip file by extension.

    Categories: caseview_template, caseview_backup, style, embedded_document,
    database, image, other.
    """
    lower = filename.lower()
    if lower.endswith(".cvw") and not lower.endswith(".bak"):
        return "caseview_template"
    if lower.endswith(".bak"):
        return "caseview_backup"
    if lower.endswith((".sty", ".cgf")):
        return "style"
    if lower.endswith((".docx", ".xlsx", ".xlsm", ".pdf", ".doc", ".xls")):
        return "embedded_document"
    if lower.endswith((".dbf", ".cdx", ".fpt")):
        return "database"
    if lower.endswith((".bmp", ".png", ".jpg", ".jpeg", ".gif", ".ico")):
        return "image"
    return "other"


def _extract_outline(ole: Any, code: str) -> dict[str, Any]:
    """Extract document outline from an open OLE2 file handle.

    Shared implementation between :class:`CwpReader` and :class:`CvwReader`.
    Reads ``Index/Bookmarks``, ``Index/Sect``, ``Index/Para``. Returns a
    dict with ``bookmarks``, ``sections``, ``paragraphs`` and any
    ``parse_warnings``.
    """
    warnings: list[str] = []

    bookmarks: list[dict[str, Any]] = []
    if ole.exists("Index/Bookmarks"):
        try:
            data = ole.openstream("Index/Bookmarks").read()
            bookmarks, bm_warn = _parse_bookmark_records(data)
            warnings.extend(f"bookmarks: {w}" for w in bm_warn)
        except Exception as e:
            warnings.append(f"bookmarks read failed: {e}")

    sections: list[dict[str, int]] = []
    if ole.exists("Index/Sect"):
        try:
            data = ole.openstream("Index/Sect").read()
            sections, sect_warn = _parse_section_index(data)
            warnings.extend(f"sections: {w}" for w in sect_warn)
        except Exception as e:
            warnings.append(f"sections read failed: {e}")

    paragraphs: list[int] = []
    if ole.exists("Index/Para"):
        try:
            data = ole.openstream("Index/Para").read()
            paragraphs, para_warn = _parse_paragraph_index(data)
            warnings.extend(f"paragraphs: {w}" for w in para_warn)
        except Exception as e:
            warnings.append(f"paragraphs read failed: {e}")

    result: dict[str, Any] = {
        "code": code,
        "bookmarks": bookmarks,
        "bookmark_count": len(bookmarks),
        "sections": sections,
        "section_count": len(sections),
        "paragraphs": paragraphs,
        "paragraph_count": len(paragraphs),
    }
    if warnings:
        result["parse_warnings"] = warnings
    return result


def _parse_bookmark_records(data: bytes) -> tuple[list[dict[str, Any]], list[str]]:
    """Parse the ``Index/Bookmarks`` OLE2 stream.

    Format (observed across Frazier-Deeter and BT Examinations samples):
      - 12-byte header: ``(u32 version, u32 header_field_1, u32 header_field_2)``
        The second/third u32s correlate with bookmark count and strings-per-
        record but not reliably — some templates have only 1 bookmark but
        header says 3. The parser drives off end-of-stream instead.
      - Repeated records, each:
          - ASCII name (2-byte LE length prefix, N bytes)
          - ASCII label (2-byte LE length prefix, N bytes; usually = name)
          - 16-byte trailer: four u32s (id/offset/flags — exact meaning TBD)

    Returns ``[{name, label, meta: [4 ints]}]`` plus a list of parse warnings.
    """
    warnings: list[str] = []
    if len(data) < 12:
        return [], [f"stream too short ({len(data)} bytes)"]

    # Header is advisory only; keep it in warnings if fields look surprising
    version, h1, h2 = struct.unpack("<3I", data[:12])
    if version != 1:
        warnings.append(f"unexpected version u32={version} (expected 1)")

    records: list[dict[str, Any]] = []
    pos = 12
    while pos + 4 <= len(data):  # need at least 2 × 2-byte length prefixes
        record_start = pos
        strings: list[str] = []
        ok = True
        for _ in range(2):  # name + label
            if pos + 2 > len(data):
                ok = False
                break
            ln = struct.unpack("<H", data[pos : pos + 2])[0]
            pos += 2
            if ln == 0 or pos + ln > len(data):
                ok = False
                break
            raw = data[pos : pos + ln]
            # Require ASCII-ish — if it's not, we've run off the end of records
            if not all(32 <= b < 127 for b in raw):
                ok = False
                break
            strings.append(raw.decode("ascii", errors="replace"))
            pos += ln

        if not ok or len(strings) < 2:
            pos = record_start
            break

        meta: list[int] = []
        if pos + 16 <= len(data):
            meta = list(struct.unpack("<4I", data[pos : pos + 16]))
            pos += 16

        records.append({"name": strings[0], "label": strings[1], "meta": meta})

    if pos < len(data):
        warnings.append(f"{len(data) - pos} trailing bytes ignored")
    return records, warnings


def _parse_section_index(data: bytes) -> tuple[list[dict[str, int]], list[str]]:
    """Parse the ``Index/Sect`` OLE2 stream.

    Format:
      - 12-byte header ``(reserved=0, signature=0xa1, count)``
      - count × 16-byte records, each four u32s. Field names are
        ``u32_0…u32_3`` because exact semantics are not confirmed (likely
        include a byte offset into ``Form/Layout`` and a paragraph range).

    Returns ``[{index, u32_0, u32_1, u32_2, u32_3}]`` plus warnings.
    """
    warnings: list[str] = []
    if len(data) < 12:
        return [], [f"stream too short ({len(data)} bytes)"]

    reserved, signature, count = struct.unpack("<3I", data[:12])
    if signature != 0xA1:
        warnings.append(f"unexpected signature 0x{signature:x} (expected 0xa1)")
    expected_size = 12 + count * 16
    if len(data) != expected_size:
        warnings.append(
            f"size mismatch: header says {count} records "
            f"(expected {expected_size} bytes), stream is {len(data)} bytes"
        )

    records: list[dict[str, int]] = []
    pos = 12
    actual_count = min(count, (len(data) - 12) // 16)
    for i in range(actual_count):
        if pos + 16 > len(data):
            break
        u0, u1, u2, u3 = struct.unpack("<4I", data[pos : pos + 16])
        records.append(
            {
                "index": i,
                "u32_0": u0,
                "u32_1": u1,
                "u32_2": u2,
                "u32_3": u3,
            }
        )
        pos += 16
    return records, warnings


def _parse_paragraph_index(data: bytes) -> tuple[list[int], list[str]]:
    """Parse the ``Index/Para`` OLE2 stream.

    Format: 12-byte header ``(reserved=0, signature=0xa1, count)`` followed
    by ``count`` u32 paragraph byte-offsets (into ``Form/Layout``).

    Returns ``[offset_u32, …]`` plus warnings.
    """
    warnings: list[str] = []
    if len(data) < 12:
        return [], [f"stream too short ({len(data)} bytes)"]

    reserved, signature, count = struct.unpack("<3I", data[:12])
    if signature != 0xA1:
        warnings.append(f"unexpected signature 0x{signature:x} (expected 0xa1)")
    expected_size = 12 + count * 4
    if len(data) != expected_size:
        warnings.append(
            f"size mismatch: header says {count} offsets "
            f"(expected {expected_size} bytes), stream is {len(data)} bytes"
        )

    actual_count = min(count, (len(data) - 12) // 4)
    offsets = list(struct.unpack(f"<{actual_count}I", data[12 : 12 + actual_count * 4]))

    # Sanity check: offsets should be monotonic ascending
    if offsets and any(offsets[i] > offsets[i + 1] for i in range(len(offsets) - 1)):
        warnings.append("offsets are not monotonic ascending")
    return offsets, warnings
