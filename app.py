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

def analyze_image(image_path):
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
            return "Screenshot", 0.9
        if "Blurry" in result:
            return "Blurry", 0.8
        return "Normal", 0.7
    except Exception:
        return "Error", 0.0

def move_to_deleted(file_path):
    src = Path(file_path)
    dst = DELETED_DIR / src.name
    shutil.move(str(src), str(dst))
    st.session_state.cleaned_count += 1

def delete_all_suggested():
    to_delete = []
    for idx, img_path in enumerate(st.session_state.image_files):
        if st.session_state.get(f"analyzed_{idx}", False):
            cat = st.session_state.get(f"cat_{idx}", "")
            if cat in ["Screenshot", "Blurry"]:
                to_delete.append((idx, img_path))
    for idx, img_path in reversed(to_delete):
        move_to_deleted(img_path)
        st.session_state.image_files.pop(idx)
        for key in [f"cat_{idx}", f"conf_{idx}", f"analyzed_{idx}"]:
            if key in st.session_state:
                del st.session_state[key]
    st.session_state.cleaned_count += len(to_delete)
    st.rerun()

def analyze_all_images():
    to_analyze = [(idx, p) for idx, p in enumerate(st.session_state.image_files) if not st.session_state.get(f"analyzed_{idx}", False)]
    if not to_analyze:
        st.info("所有图片都已分析过")
        return

    # 彩虹动画（保证只显示动画，不显示HTML源码）
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
    time.sleep(0.3)  # 确保动画显示

    for idx, img_path in to_analyze:
        category, confidence = analyze_image(img_path)
        st.session_state[f"cat_{idx}"] = category
        st.session_state[f"conf_{idx}"] = confidence
        st.session_state[f"analyzed_{idx}"] = True

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
        save_path = UPLOAD_DIR / file.name
        if not save_path.exists():
            with open(save_path, "wb") as f:
                f.write(file.getbuffer())
        if str(save_path) not in st.session_state.image_files:
            st.session_state.image_files.append(str(save_path))

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
            if st.button("分析", key=f"ana_{idx}"):
                with st.spinner("分析中..."):
                    cat, conf = analyze_image(img_path)
                    st.session_state[f"cat_{idx}"] = cat
                    st.session_state[f"conf_{idx}"] = conf
                    st.session_state[f"analyzed_{idx}"] = True
                st.rerun()
            if st.session_state.get(f"analyzed_{idx}", False):
                cat = st.session_state[f"cat_{idx}"]
                conf = st.session_state[f"conf_{idx}"]
                if cat in ["Screenshot", "Blurry"]:
                    st.markdown(f'<div style="background-color:#EE475D; padding:8px; border-radius:8px; color:white;">建议删除 ({cat})<br>置信度 {conf:.0%}</div>', unsafe_allow_html=True)
                    if st.button("删除", key=f"del_{idx}"):
                        move_to_deleted(img_path)
                        st.session_state.image_files.pop(idx)
                        for k in [f"cat_{idx}", f"conf_{idx}", f"analyzed_{idx}"]:
                            if k in st.session_state: del st.session_state[k]
                        st.rerun()
                elif cat == "Normal":
                    st.markdown(f'<div style="background-color:#6E8B74; padding:8px; border-radius:8px; color:white;">建议保留<br>置信度 {conf:.0%}</div>', unsafe_allow_html=True)

    if st.button("一键清理所有AI建议删除的图片", use_container_width=True):
        delete_all_suggested()
else:
    st.info("请先上传一些图片")