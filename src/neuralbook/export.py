"""Export NeuralBook documents to EPUB and other formats."""

from __future__ import annotations

import re
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from .format import NeuralBookDocument


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _section_to_html(section: dict) -> str:
    """Convert a NeuralBook section body to basic HTML."""
    body = section.get("body", "")
    # Escape HTML
    body = body.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Bold
    body = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", body)
    # Italic
    body = re.sub(r"\*(.+?)\*", r"<em>\1</em>", body)
    # Headers
    body = re.sub(r"^### (.+)$", r"<h3>\1</h3>", body, flags=re.MULTILINE)
    body = re.sub(r"^## (.+)$", r"<h2>\1</h2>", body, flags=re.MULTILINE)
    # Horizontal rules
    body = re.sub(r"^=====+\s*.*?\s*=+$", "<hr/>", body, flags=re.MULTILINE)
    body = re.sub(r"^---$", "<hr/>", body, flags=re.MULTILINE)
    # List items
    body = re.sub(r"^- (.+)$", r"<li>\1</li>", body, flags=re.MULTILINE)
    # Paragraphs
    paragraphs = body.split("\n\n")
    html_parts = []
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        if p.startswith("<h") or p.startswith("<hr") or p.startswith("<li"):
            html_parts.append(p)
        else:
            p = p.replace("\n", "<br/>")
            html_parts.append(f"<p>{p}</p>")
    return "\n".join(html_parts)


def export_epub(doc: NeuralBookDocument, output_path: Path) -> Path:
    """Export a NeuralBook document to EPUB format."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    book_id = uuid.uuid4().hex
    title = doc.meta.get("title", "Untitled")
    author = doc.meta.get("author", "Unknown")
    language = doc.meta.get("language", "en")
    created = doc.neuralbook.get("created", _now_iso())

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # mimetype (must be first, uncompressed)
        zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)

        # META-INF/container.xml
        zf.writestr(
            "META-INF/container.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>""",
        )

        # Build chapter files and manifest
        manifest_items = []
        spine_items = []

        for i, section in enumerate(doc.content):
            chapter_id = f"chapter_{i+1:03d}"
            filename = f"{chapter_id}.xhtml"
            sec_type = section.get("type", "section").upper()
            sec_number = section.get("number", str(i + 1))
            sec_title = section.get("title", f"Chapter {i+1}")
            body_html = _section_to_html(section)

            zf.writestr(
                f"OEBPS/{filename}",
                f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="{language}" lang="{language}">
<head>
  <meta charset="UTF-8"/>
  <title>{sec_title}</title>
  <link rel="stylesheet" type="text/css" href="style.css"/>
</head>
<body>
  <h1>{sec_type} {sec_number}: {sec_title}</h1>
  {body_html}
</body>
</html>""",
            )

            manifest_items.append(
                f'<item id="{chapter_id}" href="{filename}" media-type="application/xhtml+xml"/>'
            )
            spine_items.append(f'<itemref idref="{chapter_id}"/>')

        # CSS
        zf.writestr(
            "OEBPS/style.css",
            """body { font-family: Georgia, serif; margin: 2em; line-height: 1.6; color: #222; }
h1 { font-size: 1.8em; margin-top: 2em; border-bottom: 1px solid #ccc; padding-bottom: 0.3em; }
h2 { font-size: 1.4em; }
h3 { font-size: 1.2em; }
strong { font-weight: bold; }
em { font-style: italic; }
hr { border: none; border-top: 1px solid #ccc; margin: 2em 0; }
li { margin: 0.3em 0; }
p { margin: 0.8em 0; }""",
        )

        # content.opf
        manifest_str = "\n    ".join(manifest_items)
        spine_str = "\n    ".join(spine_items)
        zf.writestr(
            "OEBPS/content.opf",
            f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId" version="3.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="BookId">urn:uuid:{book_id}</dc:identifier>
    <dc:title>{title}</dc:title>
    <dc:creator>{author}</dc:creator>
    <dc:language>{language}</dc:language>
    <dc:date>{created}</dc:date>
    <meta property="dcterms:modified">{_now_iso()}</meta>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="style" href="style.css" media-type="text/css"/>
    {manifest_str}
  </manifest>
  <spine>
    {spine_str}
  </spine>
</package>""",
        )

        # nav.xhtml
        zf.writestr(
            "OEBPS/nav.xhtml",
            f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="{language}" lang="{language}">
<head><title>Table of Contents</title></head>
<body>
  <nav epub:type="toc" id="toc">
    <h1>Table of Contents</h1>
    <ol>
{"".join(f'      <li><a href="chapter_{i+1:03d}.xhtml">{s.get("type", "section").upper()} {s.get("number", str(i+1))}: {s.get("title", "")}</a></li>\n' for i, s in enumerate(doc.content))}
    </ol>
  </nav>
</body>
</html>""",
        )

    return output_path


def export_html(doc: NeuralBookDocument, output_path: Path) -> Path:
    """Export a NeuralBook document to a single-page HTML file."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    title = doc.meta.get("title", "Untitled")
    author = doc.meta.get("author", "")

    sections_html = []
    for section in doc.content:
        sec_type = section.get("type", "section").upper()
        sec_number = section.get("number", "")
        sec_title = section.get("title", "")
        body_html = _section_to_html(section)
        sections_html.append(
            f"""
<article id="{section.get('id', '')}">
  <h2>{sec_type} {sec_number}: {sec_title}</h2>
  {body_html}
</article>"""
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{title}</title>
  <style>
    body {{ font-family: Georgia, serif; max-width: 800px; margin: 0 auto; padding: 2em; line-height: 1.7; color: #222; }}
    h1 {{ text-align: center; border-bottom: 2px solid #333; padding-bottom: 0.5em; }}
    h2 {{ color: #333; border-bottom: 1px solid #ccc; padding-bottom: 0.3em; margin-top: 3em; }}
    article {{ margin-bottom: 4em; }}
    strong {{ color: #006; }}
    hr {{ border: none; border-top: 1px solid #ccc; margin: 2em 0; }}
    .meta {{ text-align: center; color: #666; font-size: 0.9em; margin-bottom: 3em; }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <div class="meta">by {author} | NeuralBook™ {doc.neuralbook.get('format', '')}</div>
  {''.join(sections_html)}
</body>
</html>"""

    output_path.write_text(html, encoding="utf-8")
    return output_path
