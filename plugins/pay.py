from pyrogram import filters as f
from shared_client import app
from pyrogram.types import InlineKeyboardButton as B, InlineKeyboardMarkup as M, LabeledPrice as P, PreCheckoutQuery as Q
from datetime import timedelta as T
from utils.func import add_premium_user as apu
from config import P0, OWNER_ID, ADMIN_CONTACT, JOIN_LINK

@app.on_message(f.command("pay") & f.private)
async def p(c, m):
    kb = M([
        [
            B(f"⭐ Daily Plan — 20 Stars (₹20)", callback_data="p_d")
        ],
        [
            B(f"⭐ Weekly Plan — 70 Stars (₹70)", callback_data="p_w")
        ],
        [
            B(f"⭐ Monthly Plan — 150 Stars (₹150)", callback_data="p_m")
        ],
        [
            B("💳 Buy via UPI / Contact Admin", url=ADMIN_CONTACT)
        ],
        [
            B("🎟️ Redeem Gift Code", callback_data="btn_redeem_info"),
            B("📢 Channel", url=JOIN_LINK)
        ]
    ])
    
    txt = (
        "💎 **Choose Your Premium Subscription Plan:**\n\n"
        "• ☀️ **Daily Plan (1 Day)**: `₹20`  |  `20 ⭐ Stars`\n"
        "• 🗓️ **Weekly Plan (7 Days)**: `₹70`  |  `70 ⭐ Stars`\n"
        "• 📅 **Monthly Plan (30 Days)**: `₹150`  |  `150 ⭐ Stars`\n\n"
        "⚡ **Instant Automatic Activation**: Click a Stars button below to pay directly in Telegram — subscription activates in 1 second!\n"
        "👉 For UPI / QR code payment, click **Buy via UPI** to contact Admin."
    )
    await m.reply_text(txt, reply_markup=kb)
    
@app.on_callback_query(f.regex("^p_"))
async def i(c, q):
    pl = q.data.split("_")[1]
    pi = P0[pl]
    try:
        await c.send_invoice(
            chat_id=q.from_user.id,
            title=f"Premium {pi['l']}",
            description=f"Instant access to restricted content saver for {pi['du']} {pi['u']}",
            payload=f"{pl}_{q.from_user.id}",
            currency="XTR",
            prices=[P(label=f"Premium {pi['l']}", amount=pi['s'])]
        )
        await q.answer("Invoice sent 💫 Click below to pay with Stars!")
    except Exception as e:
        await q.answer(f"Err: {e}", show_alert=True)

@app.on_pre_checkout_query()
async def pc(c, q: Q): 
    await q.answer(ok=True)

@app.on_message(f.successful_payment)
async def sp(c, m):
    p = m.successful_payment
    u = m.from_user.id
    pl = p.invoice_payload.split("_")[0]
    pi = P0[pl]
    ok, r = await apu(u, pi['du'], pi['u'])
    if ok:
        e = r + T(hours=5, minutes=30)
        d = e.strftime('%d-%b-%Y %I:%M:%S %p')
        await m.reply_text(
            f"🎉 **Payment Successful & Activated!**\n\n"
            f"💎 **Plan**: Premium {pi['l']}\n"
            f"⭐ **Stars Paid**: {p.total_amount} ⭐\n"
            f"⏰ **Valid Till**: `{d} IST`\n"
            f"🔖 **Transaction ID**: `{p.telegram_payment_charge_id}`\n\n"
            f"Thank you for your purchase! You now have unrestricted access. Use `/batch` to start."
        )
        for o in OWNER_ID:
            try:
                await c.send_message(o, f"🎉 **New Star Purchase!**\n👤 User: `{u}`\n💎 Plan: `{pi['l']}`\n⭐ Stars: `{p.total_amount}`\n🔖 Txn: `{p.telegram_payment_charge_id}`")
            except Exception:
                pass
    else:
        await m.reply_text(
            f"⚠️ Payment received but activation failed. Contact admin with Txn ID: `{p.telegram_payment_charge_id}`"
        )
        for o in OWNER_ID:
            try:
                await c.send_message(o,
                    f"⚠️ Payment issue!\nUser `{u}`\nPlan `{pi['l']}`\nTxn `{p.telegram_payment_charge_id}`\nErr: `{r}`"
                )
            except Exception:
                pass


