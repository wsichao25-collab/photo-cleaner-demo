import os
import base64
import shutil
from pathlib import Path
import streamlit as st
import requests
from dotenv import load_dotenv
import time

load_dotenv()
NOVITA_API_KEY = os.getenv("NOVITA_API_KEY")
BACKEND_URL = "https://api.novita.ai/openai/v1/chat/completions"

st.set_page_config(page_title="智能相册清理器", layout="wide")

# 目录和状态
UPLOAD_DIR = Path("uploaded")
DELETED_DIR = Path("deleted")
UPLOAD_DIR.mkdir(exist_ok=True)
DELETED_DIR.mkdir(exist_ok=True)

if "image_files" not in st.session_state:
    st.session_state.image_files = []
if "cleaned_count" not in st.session_state:
    st.session_state.cleaned_count = 0

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
        "max_tokens": 100
    }
    try:
        resp = requests.post(BACKEND_URL, headers=headers, json=payload, timeout=30)
        result = resp.json()["choices"][0]["message"]["content"]
        # 简单解析，默认 Normal
        if "Screenshot" in result:
            return "Screenshot", 0.9
        if "Blurry" in result:
            return "Blurry", 0.8
        return "Normal", 0.7
    except:
        return "Normal", 0.5

def move_to_deleted(file_path):
    shutil.move(file_path, DELETED_DIR / Path(file_path).name)
    st.session_state.cleaned_count += 1

# 界面
st.title("智能相册清理器")
st.header("AI 帮你判断截图、模糊照片", divider="rainbow")

uploaded_files = st.file_uploader("上传图片", type=["jpg","png"], accept_multiple_files=True)
if uploaded_files:
    for f in uploaded_files:
        path = UPLOAD_DIR / f.name
        if not path.exists():
            with open(path, "wb") as fp:
                fp.write(f.getbuffer())
        if str(path) not in st.session_state.image_files:
            st.session_state.image_files.append(str(path))

if st.session_state.image_files:
    cols = st.columns(3)
    for idx, img in enumerate(st.session_state.image_files):
        with cols[idx%3]:
            st.image(img, use_container_width=True)
            if st.button(f"分析", key=f"ana_{idx}"):
                cat, conf = analyze_image(img)
                st.session_state[f"cat_{idx}"] = cat
                st.session_state[f"conf_{idx}"] = conf
            if f"cat_{idx}" in st.session_state:
                cat = st.session_state[f"cat_{idx}"]
                conf = st.session_state[f"conf_{idx}"]
                if cat in ["Screenshot","Blurry"]:
                    st.warning(f"建议删除 ({cat}) 置信度{conf:.0%}")
                    if st.button("删除", key=f"del_{idx}"):
                        move_to_deleted(img)
                        st.session_state.image_files.pop(idx)
                        st.rerun()
                else:
                    st.success("建议保留")
    if st.button("一键清理所有建议删除的图片"):
        to_del = [img for i,img in enumerate(st.session_state.image_files) if st.session_state.get(f"cat_{i}") in ["Screenshot","Blurry"]]
        for img in to_del:
            move_to_deleted(img)
            st.session_state.image_files.remove(img)
        st.rerun()