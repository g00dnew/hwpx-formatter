"""
HWPX 논문 서식 설정.

단위 참고:
- font height: 1/100 pt (예: 1000 = 10pt, 1300 = 13pt, 1600 = 16pt)
- margin/spacing: HWPUNIT = 1/7200 inch (예: 8504 ≈ 3cm)
- lineSpacing value: PERCENT 타입일 때 퍼센트 값 (예: 180 = 180%)
- indent: HWPUNIT (800 ≈ 2칸 들여쓰기)
"""

FORMAT_CONFIG = {
    # 페이지 설정
    "page": {
        "landscape": "WIDELY",
        "width": 59528,
        "height": 84188,
        "margin_left": 8504,
        "margin_right": 8504,
        "margin_top": 5668,
        "margin_bottom": 4252,
        "margin_header": 4252,
        "margin_footer": 4252,
        "gutter": 0,
    },

    # 공통 줄간격
    "line_spacing_type": "PERCENT",
    "line_spacing_value": 180,

    # 스타일별 서식 정의
    # bold: True/False, size: 1/100 pt, align: LEFT/CENTER/JUSTIFY
    "styles": {
        # 본문 (기본 바탕글)
        "body": {
            "size": 1000,        # 10pt
            "bold": False,
            "align": "JUSTIFY",
            "indent": 800,       # 들여쓰기 2칸
        },
        # 논문 제목
        "title": {
            "size": 1300,        # 13pt
            "bold": True,
            "align": "CENTER",
            "indent": 0,
        },
        # 장 제목 (1. 서론, 2. 본론 등)
        "chapter": {
            "size": 1600,        # 16pt
            "bold": True,
            "align": "LEFT",
            "indent": 0,
        },
        # 절 제목 (1.1. 연구 목적)
        "section": {
            "size": 1300,        # 13pt
            "bold": True,
            "align": "LEFT",
            "indent": 0,
        },
        # 소절 제목 (2.2.1. 경제성 원리)
        "subsection": {
            "size": 1000,        # 10pt
            "bold": True,
            "align": "LEFT",
            "indent": 0,
        },
        # 국문요약 / ABSTRACT / 참고문헌 제목
        "special_heading": {
            "size": 1300,        # 13pt
            "bold": True,
            "align": "LEFT",
            "indent": 0,
        },
    },

    # 글꼴
    "font": {
        "face_hangul": "바탕체",
        "face_latin": "바탕체",
    },
}

# 제목 자동 감지 패턴 (정규식)
# section0.xml의 텍스트 내용으로 스타일 구분
HEADING_PATTERNS = {
    # 특수 제목
    "special_heading": [
        r"^국\s*문\s*요\s*약",
        r"^ABSTRACT",
        r"^참\s*고\s*문\s*헌",
    ],
    # 장 제목: "1. ", "2. " 등 (한 자리 숫자 + 점 + 공백)
    "chapter": [
        r"^\d+\.\s+\S",
    ],
    # 절 제목: "1.1. ", "2.3. " 등
    "section": [
        r"^\d+\.\d+\.\s+\S",
    ],
    # 소절 제목: "1.1.1. ", "2.2.1. " 등
    "subsection": [
        r"^\d+\.\d+\.\d+\.\s+\S",
    ],
}
