"""HWPX 논문 서식 편집기 웹 앱."""

import os
import tempfile
import shutil

from flask import Flask, request, send_file, render_template_string
from hwpx_utils import extract_hwpx, repackage_hwpx, parse_xml, save_xml, NAMESPACES
from config import FORMAT_CONFIG, HEADING_PATTERNS
from formatter import format_hwpx

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>HWPX 논문 서식 편집기</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif;
    background: #f8f9fa;
    color: #333;
    min-height: 100vh;
}
.container {
    max-width: 720px;
    margin: 0 auto;
    padding: 40px 20px;
}
h1 {
    font-size: 28px;
    font-weight: 700;
    margin-bottom: 8px;
}
.subtitle {
    color: #666;
    margin-bottom: 40px;
    font-size: 15px;
}
.upload-area {
    border: 2px dashed #ccc;
    border-radius: 16px;
    padding: 60px 40px;
    text-align: center;
    background: #fff;
    cursor: pointer;
    transition: all 0.2s;
}
.upload-area:hover, .upload-area.dragover {
    border-color: #4A90D9;
    background: #f0f6ff;
}
.upload-area.processing {
    border-color: #999;
    background: #fafafa;
    cursor: wait;
}
.upload-icon {
    font-size: 48px;
    margin-bottom: 16px;
}
.upload-text {
    font-size: 16px;
    color: #555;
    margin-bottom: 8px;
}
.upload-hint {
    font-size: 13px;
    color: #999;
}
input[type="file"] { display: none; }
.format-info {
    margin-top: 32px;
    background: #fff;
    border-radius: 12px;
    padding: 24px;
    border: 1px solid #e5e5e5;
}
.format-info h3 {
    font-size: 16px;
    margin-bottom: 16px;
    color: #333;
}
.format-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
}
.format-table th, .format-table td {
    padding: 8px 12px;
    text-align: left;
    border-bottom: 1px solid #eee;
}
.format-table th {
    color: #666;
    font-weight: 600;
    white-space: nowrap;
}
.format-table td { color: #333; }
.spinner {
    display: none;
    width: 40px; height: 40px;
    border: 4px solid #e5e5e5;
    border-top: 4px solid #4A90D9;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin: 0 auto 16px;
}
@keyframes spin { to { transform: rotate(360deg); } }
.error {
    color: #e74c3c;
    margin-top: 16px;
    font-size: 14px;
    display: none;
}
.footer {
    margin-top: 40px;
    text-align: center;
    font-size: 13px;
    color: #999;
}
</style>
</head>
<body>
<div class="container">
    <h1>HWPX 논문 서식 편집기</h1>
    <p class="subtitle">❤️❤️❤️ 채정이만을 위해 사랑을 담아 만든 서비스 ❤️❤️❤️</p>

    <div class="upload-area" id="dropZone" onclick="document.getElementById('fileInput').click()">
        <div class="spinner" id="spinner"></div>
        <div id="uploadContent">
            <div class="upload-icon">📄</div>
            <div class="upload-text">HWPX 파일을 끌어다 놓거나 클릭하세요</div>
            <div class="upload-hint">.hwpx 파일만 지원 (최대 50MB)</div>
        </div>
        <div id="processingText" style="display:none">
            <div class="upload-text">서식 변환 중...</div>
        </div>
    </div>
    <div class="error" id="errorMsg"></div>

    <input type="file" id="fileInput" accept=".hwpx">

    <div class="format-info">
        <h3>적용되는 서식</h3>
        <table class="format-table">
            <tr><th>장 제목 (1. 서론)</th><td>16pt, 굵게</td></tr>
            <tr><th>절 제목 (1.1.)</th><td>13pt, 굵게</td></tr>
            <tr><th>소절 (1.1.1.)</th><td>10pt, 굵게</td></tr>
            <tr><th>본문</th><td>10pt, 들여쓰기 2칸, 혼합정렬</td></tr>
            <tr><th>줄간격</th><td>180%</td></tr>
            <tr><th>글꼴</th><td>바탕체</td></tr>
        </table>
    </div>

    <div class="footer">HWPX 파일은 서버에 저장되지 않습니다.</div>
</div>

<script>
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const spinner = document.getElementById('spinner');
const uploadContent = document.getElementById('uploadContent');
const processingText = document.getElementById('processingText');
const errorMsg = document.getElementById('errorMsg');

['dragenter','dragover'].forEach(e => {
    dropZone.addEventListener(e, ev => { ev.preventDefault(); dropZone.classList.add('dragover'); });
});
['dragleave','drop'].forEach(e => {
    dropZone.addEventListener(e, ev => { ev.preventDefault(); dropZone.classList.remove('dragover'); });
});

dropZone.addEventListener('drop', e => {
    const file = e.dataTransfer.files[0];
    if (file) uploadFile(file);
});

fileInput.addEventListener('change', e => {
    if (e.target.files[0]) uploadFile(e.target.files[0]);
});

async function uploadFile(file) {
    if (!file.name.endsWith('.hwpx')) {
        showError('.hwpx 파일만 업로드할 수 있습니다.');
        return;
    }

    errorMsg.style.display = 'none';
    dropZone.classList.add('processing');
    spinner.style.display = 'block';
    uploadContent.style.display = 'none';
    processingText.style.display = 'block';

    const formData = new FormData();
    formData.append('file', file);

    try {
        const resp = await fetch('/format', { method: 'POST', body: formData });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.error || '변환에 실패했습니다.');
        }
        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        const baseName = file.name.replace('.hwpx', '');
        a.href = url;
        a.download = baseName + '_formatted.hwpx';
        a.click();
        URL.revokeObjectURL(url);
    } catch (e) {
        showError(e.message);
    } finally {
        dropZone.classList.remove('processing');
        spinner.style.display = 'none';
        uploadContent.style.display = 'block';
        processingText.style.display = 'none';
        fileInput.value = '';
    }
}

function showError(msg) {
    errorMsg.textContent = msg;
    errorMsg.style.display = 'block';
}
</script>
</body>
</html>"""


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/format", methods=["POST"])
def format_file():
    if "file" not in request.files:
        return {"error": "파일이 없습니다."}, 400

    file = request.files["file"]
    if not file.filename.endswith(".hwpx"):
        return {"error": ".hwpx 파일만 지원합니다."}, 400

    tmp_dir = tempfile.mkdtemp()
    try:
        input_path = os.path.join(tmp_dir, "input.hwpx")
        output_path = os.path.join(tmp_dir, "output.hwpx")
        file.save(input_path)

        format_hwpx(input_path, output_path)

        return send_file(
            output_path,
            as_attachment=True,
            download_name=file.filename.replace(".hwpx", "_formatted.hwpx"),
            mimetype="application/octet-stream",
        )
    except Exception as e:
        return {"error": f"변환 실패: {str(e)}"}, 500
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
