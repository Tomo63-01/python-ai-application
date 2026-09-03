"""Prompt builders for each writing tool."""

from __future__ import annotations

SYSTEM_RULES = """\
あなたは日本語に精通したプロのライター兼編集者です。
回答は必ず日本語で書いてください（翻訳ツールを除く）。
余計な前置きや締めの言葉は不要です。指定された成果物のみを出力してください。
"""


def blog_article(
    topic: str,
    audience: str,
    tone: str,
    length: str,
    keywords: str,
    outline: str,
) -> str:
    keyword_block = f"\n含めたいキーワード: {keywords}" if keywords.strip() else ""
    outline_block = f"\n参考構成:\n{outline}" if outline.strip() else ""
    return f"""{SYSTEM_RULES}
以下の条件でブログ記事を執筆してください。

テーマ: {topic}
想定読者: {audience or "一般読者"}
トーン: {tone}
分量の目安: {length}{keyword_block}{outline_block}

要件:
- 魅力的なタイトルを先頭に置く
- 導入・本文・まとめの構成にする
- 見出し（##）を使って読みやすくする
- 具体例や実務で使える示唆を入れる
"""


def email_reply(
    received_email: str,
    intent: str,
    tone: str,
    sender_name: str,
    extra: str,
) -> str:
    name_block = f"\n署名・差出人名: {sender_name}" if sender_name.strip() else ""
    extra_block = f"\n追加で伝えたいこと: {extra}" if extra.strip() else ""
    return f"""{SYSTEM_RULES}
以下の受信メールに対する返信文を作成してください。

受信メール:
---
{received_email}
---

返信の目的・伝えたいこと: {intent}
トーン: {tone}{name_block}{extra_block}

要件:
- 件名案も1つ付ける
- 丁寧だが冗長すぎない文面にする
- 必要に応じて確認事項や次のアクションを含める
"""


def summarize_email(email_text: str, detail: str) -> str:
    return f"""{SYSTEM_RULES}
以下のメールを要約してください。

メール本文:
---
{email_text}
---

要約の詳細度: {detail}

出力形式:
1. 一言サマリー
2. 要点（箇条書き）
3. 求められているアクション / 返信が必要か
4. 期限・重要な日付（あれば）
"""


def summarize_article(article: str, length: str, focus: str) -> str:
    focus_block = f"\n特に注目してほしい観点: {focus}" if focus.strip() else ""
    return f"""{SYSTEM_RULES}
以下の文章・記事を要約してください。

本文:
---
{article}
---

要約の長さ: {length}{focus_block}

出力形式:
1. 要約本文
2. 重要なポイント（箇条書き）
"""


def proofread(text: str, mode: str) -> str:
    return f"""{SYSTEM_RULES}
以下の文章を推敲してください。モード: {mode}

原文:
---
{text}
---

出力形式:
1. 推敲後の全文
2. 主な変更点（箇条書き、簡潔に）
"""


def change_tone(text: str, target_tone: str) -> str:
    return f"""{SYSTEM_RULES}
以下の文章を、指定のトーンに書き換えてください。

目標トーン: {target_tone}

原文:
---
{text}
---

意味は変えず、文体・語彙・丁寧さだけを調整してください。書き換えた全文のみを出力してください。
"""


def sns_post(
    topic: str,
    platform: str,
    tone: str,
    hashtags: bool,
    count: int,
) -> str:
    hashtag_rule = "ハッシュタグを適度に付ける" if hashtags else "ハッシュタグは付けない"
    return f"""{SYSTEM_RULES}
以下の条件でSNS投稿文を作成してください。

内容・テーマ: {topic}
プラットフォーム: {platform}
トーン: {tone}
候補数: {count}案
ハッシュタグ: {hashtag_rule}

各案を番号付きで出力し、文字数の目安にも配慮してください。
"""


def rewrite_text(text: str, action: str) -> str:
    action_map = {
        "言い換え": "同じ意味で自然な別表現に言い換える",
        "詳しく拡充": "内容を保ちつつ、具体例や説明を加えて詳しくする",
        "簡潔に短縮": "要点を残して簡潔に短くする",
    }
    instruction = action_map.get(action, action)
    return f"""{SYSTEM_RULES}
以下の文章を加工してください。指示: {instruction}

原文:
---
{text}
---

加工後の全文のみを出力してください。
"""


def title_ideas(content: str, count: int, style: str) -> str:
    return f"""{SYSTEM_RULES}
以下の内容に合うタイトル案を作成してください。

内容・要約:
---
{content}
---

件数: {count}案
スタイル: {style}

番号付きリストで、キャッチーかつ内容を正確に表すタイトルを出してください。
"""


def translate(text: str, target_lang: str, preserve_tone: bool) -> str:
    tone_rule = (
        "原文のトーン・丁寧さもできるだけ維持する"
        if preserve_tone
        else "自然で読みやすい表現を優先する"
    )
    return f"""あなたは優秀な翻訳者です。余計な説明はせず、翻訳結果のみを出力してください。

翻訳先言語: {target_lang}
方針: {tone_rule}

原文:
---
{text}
---
"""


def extract_action_items(text: str) -> str:
    return f"""{SYSTEM_RULES}
以下の文章（メール・議事録・メモなど）から、やるべきことと決定事項を抽出してください。

本文:
---
{text}
---

出力形式:
1. アクションアイテム（担当が分かる場合は併記、優先度が高いものから）
2. 決定事項
3. 保留・未決事項
4. 期限・日付
該当がない項目は「なし」と書いてください。
"""
