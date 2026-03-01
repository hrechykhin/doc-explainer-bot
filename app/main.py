import logging
from pathlib import Path

from telegram import Update, Document
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from .config import load_settings
from .extractors import extract_text
from .llm import LLM
from .pipeline import (
    build_map_summaries,
    explain_from_summaries,
    answer_question_from_summaries,
    summaries_to_json,
    summaries_from_json,
)
from .storage import (
    sha256_bytes,
    upsert_doc,
    get_doc,
    set_user_current_doc,
    get_user_current_doc,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
log = logging.getLogger("doc-explainer-bot")

DATA_DIR = Path("data/files")
DATA_DIR.mkdir(parents=True, exist_ok=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Send me a PDF/DOCX/TXT, then use:\n"
        "/explain — brief summary\n"
        "/ask <question> — ask about the uploaded document\n"
        "/status — what file is selected\n"
        "\nNotes: Scanned PDFs (images) are not supported in this version."
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    h = get_user_current_doc(uid)
    if not h:
        await update.message.reply_text("No document selected. Send a file first.")
        return
    rec = get_doc(h)
    if not rec:
        await update.message.reply_text(
            "Selected document not found in cache. Send it again."
        )
        return
    await update.message.reply_text(
        f"Current document: `{rec.filename}`", parse_mode=ParseMode.MARKDOWN
    )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.message
    if not msg or not msg.document:
        return

    s = context.application.bot_data["settings"]
    doc: Document = msg.document

    # Basic size check
    if doc.file_size and doc.file_size > s.max_file_mb * 1024 * 1024:
        await msg.reply_text(f"File too large. Max {s.max_file_mb} MB.")
        return

    tg_file = await doc.get_file()
    raw = await tg_file.download_as_bytearray()

    file_hash = sha256_bytes(bytes(raw))
    cached = get_doc(file_hash)
    if cached:
        set_user_current_doc(update.effective_user.id, file_hash)
        await msg.reply_text(
            f"Loaded from cache: `{cached.filename}`. Use /explain or /ask.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    filename = doc.file_name or "document"
    local_path = DATA_DIR / f"{file_hash}_{filename}"
    local_path.write_bytes(bytes(raw))

    await msg.reply_text(
        f"Extracting text from `{filename}` …", parse_mode=ParseMode.MARKDOWN
    )

    ex = extract_text(local_path)
    if not ex.ok:
        await msg.reply_text(
            f"Could not extract text: {ex.error}\n\n"
            "If this is a scanned PDF, add OCR later (e.g., Tesseract) and retry."
        )
        return

    # Store extracted text; map summaries computed on first /explain or /ask (lazy)
    upsert_doc(
        file_hash=file_hash, filename=filename, text=ex.text, map_summaries_json=None
    )
    set_user_current_doc(update.effective_user.id, file_hash)

    await msg.reply_text(
        f"Saved `{filename}`. Use /explain or /ask <question>.",
        parse_mode=ParseMode.MARKDOWN,
    )


async def explain(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.message
    if not msg:
        return

    uid = update.effective_user.id
    h = get_user_current_doc(uid)
    if not h:
        await msg.reply_text("Send a PDF/DOCX/TXT first.")
        return

    rec = get_doc(h)
    if not rec:
        await msg.reply_text("Document not found. Send it again.")
        return

    s = context.application.bot_data["settings"]
    llm: LLM = context.application.bot_data["llm"]

    summaries = summaries_from_json(rec.map_summaries_json)
    if not summaries:
        await msg.reply_text("Summarizing document (first time may take a bit) …")
        pr = build_map_summaries(
            llm=llm,
            text=rec.text,
            model_map=s.openai_model_map,
            chunk_chars=s.chunk_chars,
            overlap_chars=s.overlap_chars,
            map_summary_tokens=s.map_summary_tokens,
        )
        if not pr.ok:
            await msg.reply_text(f"Failed to summarize: {pr.error}")
            return
        summaries = pr.map_summaries
        upsert_doc(
            file_hash=rec.file_hash,
            filename=rec.filename,
            text=rec.text,
            map_summaries_json=summaries_to_json(summaries),
        )

    out = explain_from_summaries(
        llm=llm,
        filename=rec.filename,
        map_summaries=summaries,
        model_final=s.openai_model_final,
        final_tokens=s.final_tokens,
    )
    await _send_markdown(msg, out)


async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.message
    if not msg:
        return

    if not context.args:
        await msg.reply_text("Usage: /ask <question>")
        return
    question = " ".join(context.args).strip()

    uid = update.effective_user.id
    h = get_user_current_doc(uid)
    if not h:
        await msg.reply_text("Send a PDF/DOCX/TXT first.")
        return

    rec = get_doc(h)
    if not rec:
        await msg.reply_text("Document not found. Send it again.")
        return

    s = context.application.bot_data["settings"]
    llm: LLM = context.application.bot_data["llm"]

    summaries = summaries_from_json(rec.map_summaries_json)
    if not summaries:
        await msg.reply_text("Summarizing document (first time may take a bit) …")
        pr = build_map_summaries(
            llm=llm,
            text=rec.text,
            model_map=s.openai_model_map,
            chunk_chars=s.chunk_chars,
            overlap_chars=s.overlap_chars,
            map_summary_tokens=s.map_summary_tokens,
        )
        if not pr.ok:
            await msg.reply_text(f"Failed to summarize: {pr.error}")
            return
        summaries = pr.map_summaries
        upsert_doc(
            file_hash=rec.file_hash,
            filename=rec.filename,
            text=rec.text,
            map_summaries_json=summaries_to_json(summaries),
        )

    out = answer_question_from_summaries(
        llm=llm,
        filename=rec.filename,
        map_summaries=summaries,
        question=question,
        model_final=s.openai_model_final,
        final_tokens=s.final_tokens,
    )
    await _send_markdown(msg, out)


async def _send_markdown(msg, text: str) -> None:
    text = (text or "").strip()
    if not text:
        await msg.reply_text("Empty response.")
        return
    for chunk in _split_text(text, max_len=3500):
        await msg.reply_text(
            chunk, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True
        )


def _split_text(text: str, max_len: int = 3500) -> list[str]:
    if len(text) <= max_len:
        return [text]
    parts, buf = [], ""
    for line in text.splitlines(True):
        if len(buf) + len(line) > max_len:
            parts.append(buf)
            buf = ""
        buf += line
    if buf:
        parts.append(buf)
    return parts


def main() -> None:
    settings = load_settings()
    llm = LLM(api_key=settings.openai_api_key)

    app = ApplicationBuilder().token(settings.telegram_token).build()
    app.bot_data["settings"] = settings
    app.bot_data["llm"] = llm

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("explain", explain))
    app.add_handler(CommandHandler("ask", ask))

    # Accept documents (PDF/DOCX/TXT). Telegram sends them as "document".
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    app.run_polling()


if __name__ == "__main__":
    main()
