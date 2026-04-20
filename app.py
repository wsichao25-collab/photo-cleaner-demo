import os
import base64
import shutil
from pathlib import Path
import streamlit as st
import requests
import time

st.set_page_config(page_title="智能相册清理器", layout="wide")

NOVITA_API_KEY = os.getenv("NOVITA_API_KEY")
if not NOVITA_API_KEY:
    st.error("❌ 未找到 API 密钥，请在 Streamlit Cloud 的 Secrets 中设置 NOVITA_API_KEY")
    st.stop()

BACKEND_URL = "https://api.novita.ai/openai/v1/chat/completions"

UPLOAD_DIR = Path("uploaded")
DELETED_DIR = Path("deleted")
UPLOAD_DIR.mkdir(exist_ok=True)
DELETED_DIR.mkdir(exist_ok=True)

if "image_files" not in st.session_state:
    st.session_state.image_files = []
if "cleaned_count" not in st.session_state:
    st.session_state.cleaned_count = 0
if "show_main" not in st.session_state:
    st.session_state.show_main = False
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = {}

def analyze_image(image_path):
    if image_path in st.session_state.analysis_results:
        return st.session_state.analysis_results[image_path]
    with open(image_path, "rb") as f:
        img_base64 = base64.b64encode(f.read()).decode()
    headers = {"Authorization": f"Bearer {NOVITA_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "qwen/qwen3-vl-8b-instruct",
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": "判断图片属于截图、模糊还是正常，只返回JSON：{\"category\":\"Screenshot/Blurry/Normal\",\"confidence\":0.95}"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}}
            ]
        }],
        "max_tokens": 100,
        "temperature": 0.0
    }
    try:
        resp = requests.post(BACKEND_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        result = resp.json()["choices"][0]["message"]["content"]
        if "Screenshot" in result:
            cat, conf = "Screenshot", 0.9
        elif "Blurry" in result:
            cat, conf = "Blurry", 0.8
        else:
            cat, conf = "Normal", 0.7
        st.session_state.analysis_results[image_path] = (cat, conf)
        return cat, conf
    except Exception:
        st.session_state.analysis_results[image_path] = ("Error", 0.0)
        return "Error", 0.0

def move_to_deleted(file_path):
    src = Path(file_path)
    dst = DELETED_DIR / src.name
    shutil.move(str(src), str(dst))
    st.session_state.cleaned_count += 1
    if file_path in st.session_state.image_files:
        st.session_state.image_files.remove(file_path)
    if file_path in st.session_state.analysis_results:
        del st.session_state.analysis_results[file_path]

def delete_all_suggested():
    """一键删除所有建议删除的图片（修复版）"""
    to_delete = [fp for fp in st.session_state.image_files 
                 if st.session_state.analysis_results.get(fp, ("Normal",0))[0] in ["Screenshot", "Blurry"]]
    if not to_delete:
        st.info("没有可清理的图片")
        return
    deleted_count = 0
    for fp in to_delete:
        try:
            src = Path(fp)
            dst = DELETED_DIR / src.name
            shutil.move(str(src), str(dst))
            deleted_count += 1
            if fp in st.session_state.image_files:
                st.session_state.image_files.remove(fp)
            if fp in st.session_state.analysis_results:
                del st.session_state.analysis_results[fp]
        except Exception as e:
            st.error(f"删除失败 {fp}: {e}")
    st.session_state.cleaned_count += deleted_count
    if deleted_count > 0:
        st.success(f"已清理 {deleted_count} 张图片")
        time.sleep(0.5)
        st.rerun()

def analyze_all_images():
    to_analyze = [fp for fp in st.session_state.image_files if fp not in st.session_state.analysis_results]
    if not to_analyze:
        st.info("所有图片都已分析过")
        return
    anim_placeholder = st.empty()
    anim_html = """
    <div style="display: flex; justify-content: center; align-items: center; margin: 20px;">
        <div class="rainbow-spinner"></div>
    </div>
    <style>
        .rainbow-spinner {
            width: 80px;
            height: 80px;
            position: relative;
            animation: spin 1.5s linear infinite;
        }
        .rainbow-spinner::before,
        .rainbow-spinner::after {
            content: '';
            position: absolute;
            border-radius: 50%;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            box-sizing: border-box;
        }
        .rainbow-spinner::before {
            border: 8px solid rgba(255,255,255,0.2);
        }
        .rainbow-spinner::after {
            border: 8px solid transparent;
            border-top-color: #ff4d4d;
            border-right-color: #4caf50;
            border-bottom-color: #2196f3;
            border-left-color: #ffeb3b;
            animation: spin 0.8s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
    """
    anim_placeholder.markdown(anim_html, unsafe_allow_html=True)
    time.sleep(0.3)
    for fp in to_analyze:
        analyze_image(fp)
    anim_placeholder.empty()
    st.success(f"已完成 {len(to_analyze)} 张图片的分析")
    time.sleep(0.5)
    st.rerun()

# ========== 首页 ==========
if not st.session_state.show_main:
    bg_path = Path(__file__).parent / "background1.jpg"
    if bg_path.exists():
        with open(bg_path, "rb") as f:
            bg_base64 = base64.b64encode(f.read()).decode()
        bg_url = f"data:image/jpeg;base64,{bg_base64}"
    else:
        bg_url = "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=1920&q=80"

    st.markdown(f"""
    <style>
    .stApp {{ background: transparent !important; }}
    .home-bg {{
        position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: -999;
        background: url('{bg_url}') no-repeat center center; background-size: cover;
    }}
    .home-bg::after {{
        content: ""; position: absolute; top: 0; left: 0; width: 100%; height: 100%;
        background: linear-gradient(to bottom, rgba(255,255,255,0) 0%, rgba(255,255,255,0) 66%, rgba(255,255,255,1) 100%);
    }}
    .chinese-title {{
        font-family: "Helvetica Neue", "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
        font-size: 64px; font-weight: bold; color: #002FA7; text-align: center; margin-top: 20vh;
    }}
    .english-sub {{
        font-family: "Helvetica Neue", "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
        font-size: 20px; font-weight: bold; color: #002FA7; text-align: center; margin-bottom: 3rem;
    }}
    div.stButton > button {{
        background-color: white !important; color: black !important; border: 1px solid #ccc !important;
        border-radius: 30px !important; padding: 8px 32px !important;
    }}
    </style>
    <div class="home-bg"></div>
    <div class="chinese-title">做你的图片小管家</div>
    <div class="english-sub">Be your own picture manager</div>
    """, unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("点击开始", use_container_width=True):
            st.session_state.show_main = True
            st.rerun()
    st.stop()

# ========== 主界面 ==========
st.title("智能相册清理器")
st.header("AI 帮你判断截图、模糊照片", divider="rainbow")
st.markdown("上传照片，一键清理，释放空间。")

with st.sidebar:
    st.markdown("## 智能相册管家")
    st.metric("待清理图片", len(st.session_state.image_files))
    st.metric("已清理图片（本次会话）", st.session_state.cleaned_count)
    if DELETED_DIR.exists():
        deleted_files = list(DELETED_DIR.glob("*"))
        if deleted_files:
            with st.expander("回收站内容"):
                for f in deleted_files[:10]:
                    st.write(f"- {f.name}")
            if st.button("清空回收站", use_container_width=True):
                for f in deleted_files:
                    f.unlink()
                st.rerun()

uploaded_files = st.file_uploader("选择图片", type=["jpg","jpeg","png"], accept_multiple_files=True)
if uploaded_files:
    for file in uploaded_files:
        save_path = str(UPLOAD_DIR / file.name)
        if not os.path.exists(save_path):
            with open(save_path, "wb") as f:
                f.write(file.getbuffer())
        if save_path not in st.session_state.image_files:
            st.session_state.image_files.append(save_path)

if st.session_state.image_files:
    col_title, col_btn = st.columns([3, 1])
    with col_title:
        st.subheader("待清理的照片")
    with col_btn:
        if st.button("一键分析", type="primary", use_container_width=True):
            analyze_all_images()

    cols = st.columns(3)
    for idx, img_path in enumerate(st.session_state.image_files):
        with cols[idx % 3]:
            st.image(img_path, use_container_width=True)
            st.caption(Path(img_path).name)
            if st.button("分析", key=f"ana_{img_path}"):
                with st.spinner("分析中..."):
                    analyze_image(img_path)
                st.rerun()
            if img_path in st.session_state.analysis_results:
                cat, conf = st.session_state.analysis_results[img_path]
                if cat in ["Screenshot", "Blurry"]:
                    st.markdown(f'<div style="background-color:#EE475D; padding:8px; border-radius:8px; color:white;">建议删除 ({cat})<br>置信度 {conf:.0%}</div>', unsafe_allow_html=True)
                    if st.button("删除", key=f"del_{img_path}"):
                        move_to_deleted(img_path)
                        st.rerun()
                elif cat == "Normal":
                    st.markdown(f'<div style="background-color:#6E8B74; padding:8px; border-radius:8px; color:white;">建议保留<br>置信度 {conf:.0%}</div>', unsafe_allow_html=True)
                elif cat == "Error":
                    st.error("分析失败")
            else:
                st.info("点击「分析」")

    if st.button("一键清理所有AI建议删除的图片", use_container_width=True):
        delete_all_suggested()
else:
    st.info("请先上传一些图片")