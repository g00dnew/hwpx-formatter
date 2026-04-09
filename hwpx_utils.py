"""HWPX 파일 읽기/쓰기 유틸리티."""

import os
import re
import shutil
import tempfile
import zipfile
from lxml import etree

NAMESPACES = {
    "ha": "http://www.hancom.co.kr/hwpml/2011/app",
    "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
    "hp10": "http://www.hancom.co.kr/hwpml/2016/paragraph",
    "hs": "http://www.hancom.co.kr/hwpml/2011/section",
    "hc": "http://www.hancom.co.kr/hwpml/2011/core",
    "hh": "http://www.hancom.co.kr/hwpml/2011/head",
    "hm": "http://www.hancom.co.kr/hwpml/2011/master-page",
    "hwpunitchar": "http://www.hancom.co.kr/hwpml/2016/HwpUnitChar",
    "config": "urn:oasis:names:tc:opendocument:xmlns:config:1.0",
    "ooxmlchart": "http://www.hancom.co.kr/hwpml/2016/ooxmlchart",
    "epub": "http://www.idpf.org/2007/ops",
    "hhs": "http://www.hancom.co.kr/hwpml/2011/history",
    "hpf": "http://www.hancom.co.kr/schema/2011/hpf",
    "dc": "http://purl.org/dc/elements/1.1/",
    "opf": "http://www.idpf.org/2007/opf/",
}

for prefix, uri in NAMESPACES.items():
    etree.register_namespace(prefix, uri)

# XML 선언부 캐시: file_path → 원본 선언부 문자열
_xml_declarations = {}


def extract_hwpx(hwpx_path: str) -> str:
    """HWPX 파일을 임시 디렉토리에 압축 해제. 경로 반환."""
    tmp_dir = tempfile.mkdtemp(prefix="hwpx_")
    with zipfile.ZipFile(hwpx_path, "r") as z:
        z.extractall(tmp_dir)
    return tmp_dir


def repackage_hwpx(extracted_dir: str, output_path: str):
    """압축 해제된 디렉토리를 HWPX 파일로 재패키징."""
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        mimetype_path = os.path.join(extracted_dir, "mimetype")
        if os.path.exists(mimetype_path):
            zf.write(mimetype_path, "mimetype", compress_type=zipfile.ZIP_STORED)

        for root, dirs, files in os.walk(extracted_dir):
            for f in files:
                full_path = os.path.join(root, f)
                arc_name = os.path.relpath(full_path, extracted_dir)
                if arc_name == "mimetype":
                    continue
                zf.write(full_path, arc_name)


def parse_xml(file_path: str) -> etree._Element:
    """XML 파일 파싱. 원본 XML 선언부를 캐시에 보존."""
    with open(file_path, "rb") as f:
        raw = f.read()

    # 원본 XML 선언부 추출 및 캐시
    orig_str = raw.decode("utf-8")
    match = re.match(r'<\?xml[^?]*\?>\s*', orig_str)
    if match:
        _xml_declarations[os.path.abspath(file_path)] = match.group(0).rstrip()

    parser = etree.XMLParser(remove_blank_text=False)
    tree = etree.parse(file_path, parser)
    return tree


def save_xml(tree: etree._ElementTree, file_path: str):
    """XML 트리를 파일에 저장. 원본 XML 선언부 형식을 보존."""
    xml_body = etree.tostring(tree, xml_declaration=False, encoding="unicode")

    abs_path = os.path.abspath(file_path)
    declaration = _xml_declarations.get(
        abs_path,
        '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
    )

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(declaration + xml_body)
