"""明衡老師本地諮詢介面（Streamlit）。

啟動：streamlit run app/streamlit_app.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mingheng import capabilities, kb, zhuge  # noqa: E402
from mingheng.consult import Session, consult  # noqa: E402
from mingheng.providers import get_provider  # noqa: E402

DB = os.getenv("MINGHENG_DB", str(ROOT / "data" / "private" / "mingheng.sqlite"))
FIXTURE_DB = str(ROOT / "tests" / "fixtures" / "synthetic.sqlite")
OPENING = "你好，我是明衡，一位以傳統典籍為依據的 AI 命理諮詢師。你今天最想釐清的是哪一件事？"

st.set_page_config(page_title="明衡老師｜典籍命理諮詢", page_icon="☯", layout="wide")


@st.cache_resource
def get_con(path: str):
    return kb.connect(path)


def badge(status: str) -> str:
    return {"OK": "🟢 引用已核對", "DEGRADED": "🟠 已降級：部分引用無法核對", "UNCITED": "🟡 無典籍出處",
            "BLOCKED": "⚪ 模型未啟用", "ERROR": "🔴 模型錯誤"}.get(status, status)


# ---------- 側欄：資料健康、能力、起卦、清除 ----------
test_mode = st.sidebar.toggle("測試模式（合成資料）", value=False,
                              help="只用於展示流程；資料為合成，不是真實典籍。")
db_path = FIXTURE_DB if test_mode else DB
if test_mode:
    kb.ensure_fixture_db(ROOT / "tests" / "fixtures" / "synthetic_corpus.jsonl", FIXTURE_DB)
db_exists = Path(db_path).exists()
con = get_con(db_path) if db_exists else None
s = kb.stats(con) if con else {"chunks": 0, "test_fixtures": 0, "sources": [], "proof_status": {}}
if test_mode:
    s["chunks"] = s.get("test_fixtures", 0)
provider = get_provider()
p_ok, p_why = provider.available()

if test_mode:
    st.warning("⚠️ 測試模式：目前使用合成資料，所有『典籍』內容皆為虛構測試文字，不得當作真實典籍。")

st.sidebar.header("資料健康狀態")
if s["chunks"] == 0:
    st.sidebar.error("知識庫未就緒：請依 docs/DATA_SETUP.md 匯入私有資料。")
else:
    for src in s["sources"]:
        st.sidebar.success(f"{src['source_id']}《{src['book_title']}》{src['n']} 段（印刷頁 {src['p_min']}–{src['p_max']}）")
    for k, v in s["proof_status"].items():
        st.sidebar.caption(f"校對狀態 {k}: {v} 段")
st.sidebar.write(f"模型 provider：`{provider.name}` — {'可用' if p_ok else '不可用'}（{p_why}）")

with st.sidebar.expander("能力範圍", expanded=False):
    for c in capabilities.registry(s["chunks"]):
        icon = {"enabled": "✅", "reference-only": "📖", "unavailable": "⛔"}[c.status]
        st.markdown(f"{icon} **{c.name}** `{c.status}`  \n{c.reason}")

if "session" not in st.session_state:
    st.session_state.session = Session()
    st.session_state.log = []  # (role, text, result)
session: Session = st.session_state.session
session.test_mode = test_mode

st.sidebar.header("諸葛神卦起卦")
st.sidebar.caption("原書方法：三粒骰子，紅字為上卦、黑字為下卦、一粒爻數。請自擲後輸入，或用電腦亂數模擬。")
c1, c2, c3 = st.sidebar.columns(3)
up = c1.selectbox("紅（上卦）", zhuge.TRIGRAMS, key="up")
lo = c2.selectbox("黑（下卦）", zhuge.TRIGRAMS, key="lo")
yao = c3.selectbox("爻", zhuge.YAO, key="yao")
b1, b2 = st.sidebar.columns(2)
if b1.button("帶入我的擲骰結果"):
    session.cast = zhuge.cast(up, lo, yao)
    session.cast_announced = False
if b2.button("電腦模擬擲骰"):
    session.cast = zhuge.random_cast()
    session.cast_announced = False
if session.cast:
    c = session.cast
    in_kb = bool(con and kb.get(con, c.chunk_id))
    st.sidebar.info(f"本書第{c.hexagram_no}卦 {c.hexagram_name}（上{c.upper}下{c.lower}）{c.yao}爻\n\n"
                    f"印刷頁 {c.printed_page}｜PDF 約第 {c.pdf_page_estimated} 頁\n\n機制：{c.mechanism}\n\n"
                    f"{'✅ 該頁已入庫' if in_kb else '⛔ 該頁尚未入庫，明衡不會解讀'}")

if st.sidebar.button("🧹 清除本次對話（session）", type="secondary"):
    session.clear()
    st.session_state.log = []
    st.rerun()
st.sidebar.caption("對話只存在本次瀏覽器 session，不寫入檔案；請勿輸入真實身分證號、住址等個資。")

# ---------- 主畫面 ----------
st.title("明衡老師")
st.caption("AI 命理文化諮詢｜以已入庫典籍為依據；傳統命理是文化與象徵解讀，不是保證未來的科學工具。")

with st.chat_message("assistant", avatar="☯"):
    st.write(OPENING)

for role, text, res in st.session_state.log:
    with st.chat_message(role, avatar="☯" if role == "assistant" else None):
        st.write(text)
        if res is not None:
            st.caption(f"{badge(res.status)}｜{res.provider} {res.model}｜{res.latency_s:.1f}s"
                       + (f"｜風險旗標：{', '.join(res.risk_flags)}" if res.risk_flags else ""))
            if res.citations:
                with st.expander(f"來源定位（{len(res.citations)}）"):
                    for r in res.citations:
                        st.markdown(f"**{r['chunk_id']}**｜《{r['book_title']}》{r.get('section') or ''}  \n"
                                    f"印刷頁 {r.get('printed_page') or '—'}｜PDF 頁 {r.get('pdf_page') or '—'}"
                                    f"（{r.get('pdf_page_status')}）  \n層次：{r['layer']}  \n校對：{r['proof_status']}")
                        st.text(r["text"])
            elif res.status == "BLOCKED" and res.retrieved:
                with st.expander("檢索結果（未經模型解讀）"):
                    for cid in res.retrieved:
                        row = kb.get(con, cid)
                        st.markdown(f"**{cid}** {row.get('section')}")
                        st.text(row["text"])

prompt = st.chat_input("說說你想釐清的事…", disabled=con is None or s["chunks"] == 0)
if session.cast and not session.cast_announced and prompt is None:
    st.info("已帶入卦爻。可以直接問：「這一爻在說什麼？」")
if prompt:
    st.session_state.log.append(("user", prompt, None))
    with st.spinner("明衡正在查閱典籍…"):
        res = consult(con, provider, session, prompt)
    session.cast_announced = True
    st.session_state.log.append(("assistant", res.reply, res))
    st.rerun()
