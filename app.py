"""Personal AI Writing Studio — Streamlit app."""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from src import prompts
from src.gemini_client import generate_text, get_api_key, get_model_name

TOOLS = {
    "ブログ記事執筆": "blog",
    "メール返信文作成": "email_reply",
    "メール要約": "email_summary",
    "記事・文章の要約": "article_summary",
    "推敲・校正": "proofread",
    "トーン変換": "tone",
    "SNS投稿作成": "sns",
    "言い換え・拡充・短縮": "rewrite",
    "タイトル案": "titles",
    "翻訳": "translate",
    "アクション抽出": "actions",
}


def init_page() -> None:
    st.set_page_config(
        page_title="AIライティングスタジオ",
        page_icon="✍️",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            "Get help": None,
            "Report a bug": None,
            "About": "個人用 AI ライティング支援ツール（Gemini API）",
        },
    )
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.5rem; max-width: 1100px; }
        div[data-testid="stSidebar"] { background: #f7f4ef; }
        .result-box {
            background: #fafafa;
            border: 1px solid #e6e2da;
            border-radius: 8px;
            padding: 1rem 1.2rem;
            white-space: pre-wrap;
            line-height: 1.7;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    components.html(
        '<script>window.top.document.documentElement.lang = "ja";</script>',
        height=0,
    )


def render_sidebar() -> str:
    with st.sidebar:
        st.title("AIライティングスタジオ")
        st.caption("個人用ライティング支援ツール")

        tool_label = st.radio("機能を選択", list(TOOLS.keys()), index=0)

        st.divider()
        api_ok = bool(get_api_key())
        if api_ok:
            st.success("API キー設定済み", icon="✅")
            st.caption(f"モデル: `{get_model_name()}`")
        else:
            st.error("API キー未設定", icon="⚠️")
            st.caption(".env に GEMINI_API_KEY を設定してください")

        st.divider()
        st.markdown(
            """
            **使い方**
            1. 左から機能を選ぶ
            2. 入力欄を埋める
            3. 生成ボタンを押す
            """
        )
    return tool_label


def run_generation(prompt: str, temperature: float = 0.7) -> None:
    if "last_result" not in st.session_state:
        st.session_state.last_result = ""

    with st.spinner("Gemini が生成中です..."):
        try:
            result = generate_text(prompt, temperature=temperature)
            st.session_state.last_result = result
        except Exception as exc:  # noqa: BLE001 — show any API/config error in UI
            st.error(str(exc))
            return

    st.subheader("生成結果")
    st.markdown(st.session_state.last_result)
    st.download_button(
        "結果をテキスト保存",
        data=st.session_state.last_result,
        file_name="生成結果.txt",
        mime="text/plain",
    )


def ui_blog() -> None:
    st.header("ブログ記事執筆")
    st.write("テーマと条件を指定すると、構成付きのブログ記事を生成します。")

    topic = st.text_input("テーマ・タイトル案 *", placeholder="例: 朝の習慣で生産性を上げる方法")
    col1, col2 = st.columns(2)
    with col1:
        audience = st.text_input("想定読者", placeholder="例: 忙しい会社員")
        tone = st.selectbox(
            "トーン",
            ["親しみやすい", "専門的・解説調", "ストーリー調", "カジュアル", "フォーマル"],
        )
    with col2:
        length = st.selectbox("分量", ["短め（約800字）", "標準（約1500字）", "長め（約2500字）"])
        keywords = st.text_input("キーワード（任意）", placeholder="例: 習慣化, 朝活")

    outline = st.text_area("参考構成・含めてほしい内容（任意）", height=100)
    if st.button("記事を生成", type="primary", use_container_width=True):
        if not topic.strip():
            st.warning("テーマを入力してください。")
            return
        prompt = prompts.blog_article(topic, audience, tone, length, keywords, outline)
        run_generation(prompt, temperature=0.8)


def ui_email_reply() -> None:
    st.header("メール返信文作成")
    st.write("受信メールと返信意図から、使える返信文を作成します。")

    received = st.text_area("受信メール全文 *", height=200)
    intent = st.text_area("返信で伝えたいこと *", height=100, placeholder="例: 日程変更を依頼し、候補日を3つ提示する")
    col1, col2 = st.columns(2)
    with col1:
        tone = st.selectbox("トーン", ["丁寧・ビジネス", "やや砕けた丁寧", "簡潔・実務的", "温かみのある丁寧"])
    with col2:
        sender_name = st.text_input("自分の署名名（任意）", placeholder="例: 山田太郎")
    extra = st.text_input("追加指示（任意）", placeholder="例: 謝罪を一文入れる")

    if st.button("返信文を生成", type="primary", use_container_width=True):
        if not received.strip() or not intent.strip():
            st.warning("受信メールと返信意図を入力してください。")
            return
        prompt = prompts.email_reply(received, intent, tone, sender_name, extra)
        run_generation(prompt, temperature=0.6)


def ui_email_summary() -> None:
    st.header("メール要約")
    st.write("長いメールを要点・アクション・期限に整理します。")

    email_text = st.text_area("メール全文 *", height=250)
    detail = st.selectbox("詳細度", ["簡潔", "標準", "詳細"])

    if st.button("要約する", type="primary", use_container_width=True):
        if not email_text.strip():
            st.warning("メール本文を入力してください。")
            return
        prompt = prompts.summarize_email(email_text, detail)
        run_generation(prompt, temperature=0.3)


def ui_article_summary() -> None:
    st.header("記事・文章の要約")
    st.write("ブログ、レポート、長文メモなどを読みやすい要約にします。")

    article = st.text_area("要約したい文章 *", height=280)
    col1, col2 = st.columns(2)
    with col1:
        length = st.selectbox("要約の長さ", ["超簡潔（3行程度）", "標準", "詳細"])
    with col2:
        focus = st.text_input("注目観点（任意）", placeholder="例: 実践手順だけ")

    if st.button("要約する", type="primary", use_container_width=True):
        if not article.strip():
            st.warning("文章を入力してください。")
            return
        prompt = prompts.summarize_article(article, length, focus)
        run_generation(prompt, temperature=0.3)


def ui_proofread() -> None:
    st.header("推敲・校正")
    st.write("誤字・冗長さ・わかりにくさを直して、読みやすい日本語に整えます。")

    text = st.text_area("推敲したい文章 *", height=250)
    mode = st.selectbox(
        "モード",
        [
            "軽く校正（誤字・表現の修正中心）",
            "しっかり推敲（構成・読みやすさも改善）",
            "ビジネス文書向けに整える",
        ],
    )

    if st.button("推敲する", type="primary", use_container_width=True):
        if not text.strip():
            st.warning("文章を入力してください。")
            return
        prompt = prompts.proofread(text, mode)
        run_generation(prompt, temperature=0.4)


def ui_tone() -> None:
    st.header("トーン変換")
    st.write("意味はそのまま、話し方・丁寧さだけを変えたいときに使います。")

    text = st.text_area("変換したい文章 *", height=220)
    target = st.selectbox(
        "目標トーン",
        [
            "フォーマルなビジネス文体",
            "やわらかい丁寧語",
            "カジュアル",
            "簡潔・箇条書き寄り",
            "親しみのあるブランドトーン",
        ],
    )

    if st.button("トーン変換する", type="primary", use_container_width=True):
        if not text.strip():
            st.warning("文章を入力してください。")
            return
        prompt = prompts.change_tone(text, target)
        run_generation(prompt, temperature=0.5)


def ui_sns() -> None:
    st.header("SNS投稿作成")
    st.write("X / Instagram / LinkedIn 向けの投稿案を複数作成します。")

    topic = st.text_area("投稿したい内容・テーマ *", height=140)
    col1, col2, col3 = st.columns(3)
    with col1:
        platform = st.selectbox("プラットフォーム", ["X (Twitter)", "Instagram", "LinkedIn", "Facebook", "汎用"])
    with col2:
        tone = st.selectbox("トーン", ["砕けた口語", "知的・落ち着き", "情熱的", "ビジネス向け"])
    with col3:
        count = st.slider("候補数", 1, 5, 3)
    hashtags = st.checkbox("ハッシュタグを付ける", value=True)

    if st.button("投稿案を生成", type="primary", use_container_width=True):
        if not topic.strip():
            st.warning("内容を入力してください。")
            return
        prompt = prompts.sns_post(topic, platform, tone, hashtags, count)
        run_generation(prompt, temperature=0.85)


def ui_rewrite() -> None:
    st.header("言い換え・拡充・短縮")
    st.write("同じ内容を、別の言い方・もっと詳しく・もっと短く、切り替えて加工します。")

    text = st.text_area("元の文章 *", height=220)
    action = st.radio("加工タイプ", ["言い換え", "詳しく拡充", "簡潔に短縮"], horizontal=True)

    if st.button("加工する", type="primary", use_container_width=True):
        if not text.strip():
            st.warning("文章を入力してください。")
            return
        prompt = prompts.rewrite_text(text, action)
        run_generation(prompt, temperature=0.6)


def ui_titles() -> None:
    st.header("タイトル案")
    st.write("記事・企画・スライドなどのタイトル候補を出します。")

    content = st.text_area("内容の概要 *", height=180, placeholder="記事の要点や書きたいテーマを入力")
    col1, col2 = st.columns(2)
    with col1:
        count = st.slider("候補数", 3, 15, 8)
    with col2:
        style = st.selectbox(
            "スタイル",
            ["標準・わかりやすい", "キャッチー・煽り気味", "SEO向け", "知的・専門的"],
        )

    if st.button("タイトル案を生成", type="primary", use_container_width=True):
        if not content.strip():
            st.warning("内容を入力してください。")
            return
        prompt = prompts.title_ideas(content, count, style)
        run_generation(prompt, temperature=0.9)


def ui_translate() -> None:
    st.header("翻訳")
    st.write("ライティング向けに、自然な訳文へ変換します。")

    text = st.text_area("翻訳したい文章 *", height=220)
    col1, col2 = st.columns(2)
    with col1:
        target = st.selectbox(
            "翻訳先",
            ["英語", "日本語", "中国語（簡体字）", "韓国語", "フランス語", "ドイツ語", "スペイン語"],
        )
    with col2:
        preserve = st.checkbox("原文のトーンをできるだけ維持", value=True)

    if st.button("翻訳する", type="primary", use_container_width=True):
        if not text.strip():
            st.warning("文章を入力してください。")
            return
        prompt = prompts.translate(text, target, preserve)
        run_generation(prompt, temperature=0.3)


def ui_actions() -> None:
    st.header("アクション抽出")
    st.write("メール・議事録・メモから、やるべきことと決定事項を抜き出します。")

    text = st.text_area("元テキスト *", height=280)

    if st.button("抽出する", type="primary", use_container_width=True):
        if not text.strip():
            st.warning("テキストを入力してください。")
            return
        prompt = prompts.extract_action_items(text)
        run_generation(prompt, temperature=0.3)


TOOL_RENDERERS = {
    "blog": ui_blog,
    "email_reply": ui_email_reply,
    "email_summary": ui_email_summary,
    "article_summary": ui_article_summary,
    "proofread": ui_proofread,
    "tone": ui_tone,
    "sns": ui_sns,
    "rewrite": ui_rewrite,
    "titles": ui_titles,
    "translate": ui_translate,
    "actions": ui_actions,
}


def main() -> None:
    init_page()
    tool_label = render_sidebar()
    tool_key = TOOLS[tool_label]
    TOOL_RENDERERS[tool_key]()


if __name__ == "__main__":
    main()
