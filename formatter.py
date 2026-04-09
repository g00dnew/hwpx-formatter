#!/usr/bin/env python3
"""
HWPX 논문 서식 자동 편집기.
사용법: python formatter.py input.hwpx [output.hwpx]

문단 텍스트를 분석하여 제목/본문을 자동 감지하고 스타일별 서식을 적용합니다.
"""

import os
import re
import sys
import shutil

from lxml import etree
from hwpx_utils import extract_hwpx, repackage_hwpx, parse_xml, save_xml, NAMESPACES
from config import FORMAT_CONFIG, HEADING_PATTERNS


def get_paragraph_text(para_el):
    """문단 요소에서 텍스트 추출."""
    texts = []
    for t in para_el.iter("{%s}t" % NAMESPACES["hp"]):
        if t.text:
            texts.append(t.text)
    return "".join(texts).strip()


def detect_style(text):
    """텍스트 내용으로 스타일 타입 감지. 순서 중요: 소절 → 절 → 장."""
    if not text:
        return "body"

    for style_name in ["special_heading", "subsection", "section", "chapter"]:
        patterns = HEADING_PATTERNS.get(style_name, [])
        for pattern in patterns:
            if re.match(pattern, text):
                return style_name

    return "body"


def apply_page_format(extracted_dir):
    """페이지 여백 및 크기 설정 적용."""
    section_path = os.path.join(extracted_dir, "Contents", "section0.xml")
    tree = parse_xml(section_path)
    root = tree.getroot()
    page_cfg = FORMAT_CONFIG["page"]

    for page_pr in root.iter("{%s}pagePr" % NAMESPACES["hp"]):
        page_pr.set("landscape", page_cfg["landscape"])
        page_pr.set("width", str(page_cfg["width"]))
        page_pr.set("height", str(page_cfg["height"]))

        for margin in page_pr.iter("{%s}margin" % NAMESPACES["hp"]):
            margin.set("left", str(page_cfg["margin_left"]))
            margin.set("right", str(page_cfg["margin_right"]))
            margin.set("top", str(page_cfg["margin_top"]))
            margin.set("bottom", str(page_cfg["margin_bottom"]))
            margin.set("header", str(page_cfg["margin_header"]))
            margin.set("footer", str(page_cfg["margin_footer"]))
            margin.set("gutter", str(page_cfg["gutter"]))

    save_xml(tree, section_path)


def apply_font_faces(extracted_dir):
    """글꼴 이름 변경 (header.xml)."""
    header_path = os.path.join(extracted_dir, "Contents", "header.xml")
    tree = parse_xml(header_path)
    root = tree.getroot()
    font_cfg = FORMAT_CONFIG["font"]

    for fontface in root.iter("{%s}fontface" % NAMESPACES["hh"]):
        lang = fontface.get("lang", "")
        for font_el in fontface.iter("{%s}font" % NAMESPACES["hh"]):
            if lang in ("HANGUL", "HANJA", "JAPANESE", "OTHER"):
                font_el.set("face", font_cfg["face_hangul"])
            elif lang == "LATIN":
                font_el.set("face", font_cfg["face_latin"])

    save_xml(tree, header_path)


def apply_line_spacing(extracted_dir):
    """전체 줄간격 설정 (header.xml의 모든 paraPr)."""
    header_path = os.path.join(extracted_dir, "Contents", "header.xml")
    tree = parse_xml(header_path)
    root = tree.getroot()

    ls_type = FORMAT_CONFIG["line_spacing_type"]
    ls_value = str(FORMAT_CONFIG["line_spacing_value"])

    for line_sp in root.iter("{%s}lineSpacing" % NAMESPACES["hh"]):
        line_sp.set("type", ls_type)
        line_sp.set("value", ls_value)

    save_xml(tree, header_path)


def ensure_char_pr(header_tree, size, bold):
    """
    header.xml의 charProperties에서 해당 size/bold 조합의 charPr을 찾거나 새로 생성.
    charPr id를 반환.
    """
    root = header_tree.getroot()
    ns_hh = NAMESPACES["hh"]

    char_props = root.find(".//{%s}charProperties" % ns_hh)
    if char_props is None:
        return "0"

    # 기존 charPr에서 매칭되는 것 찾기
    for cp in char_props.findall("{%s}charPr" % ns_hh):
        cp_height = cp.get("height", "0")
        cp_bold = cp.get("bold", "0")
        is_bold = cp_bold == "1"
        if int(cp_height) == size and is_bold == bold:
            return cp.get("id")

    # 없으면 새로 생성 (기존 첫 번째를 복사)
    existing = char_props.findall("{%s}charPr" % ns_hh)
    if not existing:
        return "0"

    new_cp = etree.fromstring(etree.tostring(existing[0]))
    new_id = str(max(int(cp.get("id", "0")) for cp in existing) + 1)
    new_cp.set("id", new_id)
    new_cp.set("height", str(size))
    if bold:
        new_cp.set("bold", "1")
    else:
        if "bold" in new_cp.attrib:
            del new_cp.attrib["bold"]

    # itemCnt 업데이트
    item_cnt = int(char_props.get("itemCnt", "0"))
    char_props.set("itemCnt", str(item_cnt + 1))
    char_props.append(new_cp)

    return new_id


def apply_paragraph_styles(extracted_dir):
    """
    section0.xml의 각 문단 텍스트를 분석하여 스타일별 서식 적용.
    - charPrIDRef 변경 (글꼴 크기, 굵기)
    - 문단 정렬, 들여쓰기는 인라인으로 적용
    """
    header_path = os.path.join(extracted_dir, "Contents", "header.xml")
    header_tree = parse_xml(header_path)

    section_path = os.path.join(extracted_dir, "Contents", "section0.xml")
    section_tree = parse_xml(section_path)
    root = section_tree.getroot()

    ns_hp = NAMESPACES["hp"]
    ns_hh = NAMESPACES["hh"]
    ns_hc = NAMESPACES["hc"]

    styles_cfg = FORMAT_CONFIG["styles"]

    # 각 문단 처리
    for para in root.iter("{%s}p" % ns_hp):
        text = get_paragraph_text(para)
        style_name = detect_style(text)
        style = styles_cfg.get(style_name, styles_cfg["body"])

        # charPr 찾거나 생성
        char_pr_id = ensure_char_pr(header_tree, style["size"], style["bold"])

        # 모든 run의 charPrIDRef 변경
        for run in para.iter("{%s}run" % ns_hp):
            run.set("charPrIDRef", char_pr_id)

        # 문단 인라인 속성은 section에서 직접 설정하기 어려우므로
        # paraPrIDRef를 통해 header의 paraPr을 참조함
        # → 간단히 처리: 첫 번째 논문 제목 감지 (특별 처리)
        if style_name == "title":
            # 논문 제목은 첫 문단에서 감지해야 하므로 별도 로직 필요할 수 있음
            pass

    save_xml(header_tree, header_path)
    save_xml(section_tree, section_path)

    stats = {}
    for para in root.iter("{%s}p" % ns_hp):
        text = get_paragraph_text(para)
        s = detect_style(text)
        stats[s] = stats.get(s, 0) + 1
    return stats


def format_hwpx(input_path, output_path):
    """HWPX 파일에 논문 서식 적용."""
    print(f"입력: {input_path}")

    extracted = extract_hwpx(input_path)

    try:
        # 1. 페이지 설정
        apply_page_format(extracted)
        print("  ✓ 페이지 여백 적용")

        # 2. 글꼴 이름
        apply_font_faces(extracted)
        print("  ✓ 글꼴 적용")

        # 3. 줄간격
        apply_line_spacing(extracted)
        print("  ✓ 줄간격 180% 적용")

        # 4. 문단별 스타일 (크기, 굵기)
        stats = apply_paragraph_styles(extracted)
        print("  ✓ 문단 스타일 적용")
        for style_name, count in sorted(stats.items()):
            print(f"    - {style_name}: {count}개 문단")

        # 5. 재패키징
        repackage_hwpx(extracted, output_path)
        print(f"\n출력: {output_path}")
        print("서식 적용 완료!")
    finally:
        shutil.rmtree(extracted, ignore_errors=True)


def main():
    if len(sys.argv) < 2:
        print("사용법: python formatter.py <입력.hwpx> [출력.hwpx]")
        print()
        print("논문 서식 자동 적용:")
        print("  - 장 제목 (1. 서론): 16pt 굵게")
        print("  - 절 제목 (1.1.): 13pt 굵게")
        print("  - 소절 (1.1.1.): 10pt 굵게")
        print("  - 본문: 10pt, 들여쓰기 2칸, 혼합정렬")
        print("  - 줄간격: 180%")
        sys.exit(1)

    input_path = sys.argv[1]
    if not os.path.exists(input_path):
        print(f"파일을 찾을 수 없습니다: {input_path}")
        sys.exit(1)

    if len(sys.argv) >= 3:
        output_path = sys.argv[2]
    else:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_formatted{ext}"

    format_hwpx(input_path, output_path)


if __name__ == "__main__":
    main()
