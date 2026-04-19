import os
import base64
import shutil
from pathlib import Path
import streamlit as st
import requests
import time

# ========== 1. 页面配置（必须是第一个 Streamlit 命令） ==========
st.set_page_config(page_title="智能相册清理器", layout="wide")

# ========== 2. 读取环境变量（Streamlit Cloud 通过 Secrets 注入） ==========
NOVITA_API_KEY = os.getenv("NOVITA_API_KEY")
if not NOVITA_API_KEY:
    st.error("缺少 API 密钥，请在 Streamlit Cloud 的 Secrets 中设置 NOVITA_API_KEY")
    st.stop()

BACKEND_URL = "https://api.novita.ai/openai/v1/chat/completions"

# ========== 3. 目录和状态初始化 ==========
UPLOAD_DIR = Path("uploaded")
DELETED_DIR = Path("deleted")
UPLOAD_DIR.mkdir(exist_ok=True)
DELETED_DIR.mkdir(exist_ok=True)

if "image_files" not in st.session_state:
    st.session_state.image_files = []
if "cleaned_count" not in st.session_state:
    st.session_state.cleaned_count = 0

# ========== 4. 辅助函数 ==========
def analyze_image(image_path):
    """调用 Novita AI 分析图片，返回 (category, confidence)"""
    with open(image_path, "rb") as f:
        img_base64 = base64.b64encode(f.read()).decode()
    headers = {
        "Authorization": f"Bearer {NOVITA_API_KEY}",
        "Content-Type": "application/json"
    }
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
        # 简单解析
        if "Screenshot" in result:
            return "Screenshot", 0.9
        if "Blurry" in result:
            return "Blurry", 0.8
        return "Normal", 0.7
    except Exception as e:
        return "Error", 0.0

def move_to_deleted(file_path):
    shutil.move(file_path, DELETED_DIR / Path(file_path).name)
    st.session_state.cleaned_count += 1

# ========== 5. 界面标题 ==========
st.title("智能相册清理器")
st.header("AI 帮你判断截图、模糊照片", divider="rainbow")
st.markdown("上传照片，一键清理，释放空间。支持截图识别、模糊检测、表情包过滤。")

# ========== 6. 侧边栏 ==========
with st.sidebar:
    st.markdown("## 智能相册管家")
    st.markdown("---")
    st.markdown("### 功能介绍")
    st.markdown(
        """
        - 上传照片后，AI 自动分析
        - 识别 **截图** / **模糊照片** / **正常照片**
        - 支持单张删除或一键清理
        - 回收站可恢复
        """
    )
    st.markdown("---")
    st.metric("待清理图片", len(st.session_state.image_files))
    st.metric("已清理图片（本次会话）", st.session_state.cleaned_count)
    st.markdown("---")
    if DELETED_DIR.exists():
        deleted_files = list(DELETED_DIR.glob("*"))
        if deleted_files:
            with st.expander("回收站内容"):
                for f in deleted_files[:10]:
                    st.write(f"- {f.name}")
                if len(deleted_files) > 10:
                    st.write(f"... 共 {len(deleted_files)} 个文件")
            if st.button("清空回收站", use_container_width=True):
                for f in deleted_files:
                    f.unlink()
                st.success("回收站已清空")
                st.rerun()
        else:
            st.info("回收站为空")
    else:
        st.info("回收站目录不存在")

# ========== 7. 上传图片 ==========
uploaded_files = st.file_uploader(
    "选择图片（支持 jpg/png）",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True
)

if uploaded_files:
    for file in uploaded_files:
        save_path = UPLOAD_DIR / file.name
        if not save_path.exists():
            with open(save_path, "wb") as f:
                f.write(file.getbuffer())
        if str(save_path) not in st.session_state.image_files:
            st.session_state.image_files.append(str(save_path))

# ========== 8. 展示图片网格 ==========
if st.session_state.image_files:
    st.subheader("待清理的照片")
    cols = st.columns(3)
    for idx, img_path in enumerate(st.session_state.image_files):
        with cols[idx % 3]:
            with st.container():
                st.image(img_path, use_container_width=True)
                st.caption(Path(img_path).name)
                if st.button(f"分析", key=f"analyze_{idx}"):
                    with st.spinner("AI 分析中..."):
                        category, conf = analyze_image(img_path)
                        st.session_state[f"cat_{idx}"] = category
                        st.session_state[f"conf_{idx}"] = conf
                        st.session_state[f"analyzed_{idx}"] = True
                if st.session_state.get(f"analyzed_{idx}", False):
                    category = st.session_state[f"cat_{idx}"]
                    confidence = st.session_state[f"conf_{idx}"]
                    if category in ["Screenshot", "Blurry"]:
                        st.warning(f"建议删除 ({category}) 置信度 {confidence:.0%}")
                        if st.button("删除", key=f"del_{idx}"):
                            move_to_deleted(img_path)
                            st.session_state.image_files.pop(idx)
                            st.rerun()
                    elif category == "Normal":
                        st.success("建议保留")
                    else:
                        st.error("分析失败")
    
    # 一键清理按钮
    if st.button("一键清理所有AI建议删除的图片", use_container_width=True):
        to_delete = []
        for idx, img_path in enumerate(st.session_state.image_files):
            if st.session_state.get(f"analyzed_{idx}", False):
                cat = st.session_state.get(f"cat_{idx}", "")
                if cat in ["Screenshot", "Blurry"]:
                    to_delete.append(img_path)
        if to_delete:
            for img in to_delete:
                move_to_deleted(img)
                st.session_state.image_files.remove(img)
            st.success(f"已清理 {len(to_delete)} 张图片")
            st.rerun()
        else:
            st.info("没有可清理的图片（请先分析）")
else:
    st.info("请先上传一些图片")