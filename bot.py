#!/usr/bin/env python3
"""
CV Optimizer Telegram Bot
Run: TELEGRAM_BOT_TOKEN=your_token python3 bot.py
"""

import os
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)
from optimizer import run_optimizer

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

GET_JD = 1
GET_CV  = 2


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "🎯 *CV Optimizer*\n\n"
        "I'll rewrite your CV to perfectly match any job and score 97%+.\n\n"
        "Step 1 of 2 — Paste the *job description* now:",
        parse_mode="Markdown"
    )
    return GET_JD


async def receive_jd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["jd"] = update.message.text.strip()
    await update.message.reply_text(
        "✅ Got it.\n\n"
        "Step 2 of 2 — Now paste your *CV*:",
        parse_mode="Markdown"
    )
    return GET_CV


async def receive_cv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cv  = update.message.text.strip()
    jd  = context.user_data.get("jd", "").strip()

    if not jd:
        await update.message.reply_text("⚠️ Session expired. Send /start to begin again.")
        return ConversationHandler.END

    status_msg = await update.message.reply_text("🚀 *Optimizer running...*", parse_mode="Markdown")

    final = None
    for update_data in run_optimizer(cv, jd, target=97):
        step = update_data["step"]

        if step == "status":
            try:
                await status_msg.edit_text(update_data["message"], parse_mode="MarkdownV2")
            except Exception:
                pass

        elif step == "done":
            final = update_data

    if not final:
        await status_msg.edit_text("❌ Something went wrong. Send /start to try again.")
        return ConversationHandler.END

    original   = final["original_score"]
    result     = final["final_score"]
    optimized_cv = final["optimized_cv"]

    before = original.get("total_score", 0)
    after  = result.get("total_score", 0)
    delta  = after - before

    verdict = "🟢 Strong hire" if after >= 97 else "🟡 Good" if after >= 90 else "🔴 Needs work"

    summary = (
        f"✅ *Done\\!*\n\n"
        f"*Score*\n"
        f"Before: `{before}%`\n"
        f"After: `{after}%` \\(\\+{delta}%\\)\n"
        f"Verdict: {verdict}\n\n"
        f"*Breakdown*\n"
        f"🔑 Keyword Match: `{result.get('keyword_match', 0)}%`\n"
        f"💼 Experience Relevance: `{result.get('experience_relevance', 0)}%`\n"
        f"📈 Seniority Fit: `{result.get('seniority_fit', 0)}%`\n"
        f"🗣 Language Alignment: `{result.get('language_alignment', 0)}%`"
    )
    await status_msg.edit_text(summary, parse_mode="MarkdownV2")

    # Send the CV
    await update.message.reply_text("📄 *Your Optimized CV \\(1 page\\):*", parse_mode="MarkdownV2")

    chunk_size = 4000
    for i in range(0, len(optimized_cv), chunk_size):
        await update.message.reply_text(
            f"```\n{optimized_cv[i:i+chunk_size]}\n```",
            parse_mode="Markdown"
        )

    await update.message.reply_text("Send /start to optimize another CV.")
    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Cancelled. Send /start to begin again.")
    return ConversationHandler.END


def main():
    if not BOT_TOKEN:
        print("ERROR: Set TELEGRAM_BOT_TOKEN environment variable.")
        return

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            GET_JD: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_jd)],
            GET_CV: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_cv)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv)

    print("🤖 CV Optimizer Bot running...")
    # drop_pending_updates=True skips any messages sent while bot was offline
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
