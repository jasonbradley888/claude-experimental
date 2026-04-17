"""Offline CaseView template package reader — no COM/Windows dependency.

Parses .cwp template packages to extract template structure and cell/field
inventories using only file-based parsing (ZIP, XML, OLE2).

Works on Mac, Linux, and Windows.
"""

from __future__ import annotations

import io
import re
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
        self._manifest_xml = self._outer_zip.read("manifest.xml").decode("utf-8")
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
