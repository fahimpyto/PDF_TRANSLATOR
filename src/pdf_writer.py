import os
import fitz


def create_bengali_pdf(pages_data, output_path, font_path):
    font_abs_path = os.path.abspath(font_path).replace("\\", "/")
    margin = 50
    width, height = fitz.paper_size("a4")
    rect = fitz.Rect(margin, margin, width - margin, height - margin)

    doc = fitz.open()

    css = f"""@font-face {{ font-family: 'Bangla'; src: url('{font_abs_path}'); }}
body {{ font-family: 'Bangla'; font-size: 12pt; line-height: 1.8; margin: 0; padding: 0; color: #000; }}
h2 {{ font-size: 14pt; margin: 0 0 0.5em 0; }}
p {{ margin: 0 0 0.5em 0; text-align: justify; text-indent: 1.5em; }}"""

    for i, page_data in enumerate(pages_data):
        page_no = page_data["page_no"]
        text = page_data["text"]

        page = doc.new_page()

        paragraphs = text.strip().split("\n")
        para_html = "".join(f"<p>{p.strip()}</p>" for p in paragraphs if p.strip())

        html = f"""<html lang="bn"><body>
<h2>\u09AA\u09C3\u09B7\u09CD\u09A0\u09BE {page_no}</h2>
{para_html}
</body></html>"""

        page.insert_htmlbox(rect, html, css=css)

    doc.save(output_path)
    doc.close()
