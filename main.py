import logging
import sqlite3
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters
)

# ================= Configuration =================
BOT_TOKEN = "8259678073:AAG31SOAJ0Pe-Hs17V-Tphl855kGHWrHlt0"
ADMIN_ID = 7523903272
ADMIN_USERNAME = "@Musfikul018"
DEPOSIT_NUMBER = "01570298182"

# Logging Setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ================= Database Functions =================
def init_db():
    conn = sqlite3.connect('shop_bot.db')
    cursor = conn.cursor()
    
    # Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            username TEXT,
            balance REAL DEFAULT 0.0
        )
    ''')
    
    # Products Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            price REAL
        )
    ''')
    
    # Stocks Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stocks (
            stock_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            item_data TEXT
        )
    ''')
    
    # Orders Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            item_name TEXT,
            item_data TEXT,
            price REAL,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

def get_db():
    return sqlite3.connect('shop_bot.db')

def register_user(user):
    conn = get_db()
    cursor = conn.cursor()
    username = f"@{user.username}" if user.username else "N/A"
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, full_name, username, balance)
        VALUES (?, ?, ?, 0.0)
    ''', (user.id, user.full_name, username))
    conn.commit()
    conn.close()

# Main Menu Keyboard
def get_main_keyboard(user_id):
    keyboard = [
        [KeyboardButton("🛒 Buy Products"), KeyboardButton("💰 Add Balance")],
        [KeyboardButton("📦 My Orders"), KeyboardButton("💳 My Balance")],
        [KeyboardButton("🎧 Support")]
    ]
    if user_id == ADMIN_ID:
        keyboard.append([KeyboardButton("⚙️ Admin Control Panel")])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Admin Panel Keyboard
def get_admin_keyboard():
    keyboard = [
        [InlineKeyboardButton("➕ Add Product", callback_data="admin_add_prod"),
         InlineKeyboardButton("📦 Add Stock Code", callback_data="admin_add_stock")],
        [InlineKeyboardButton("➕ Add User Balance", callback_data="admin_add_bal"),
         InlineKeyboardButton("👥 View All Users", callback_data="admin_view_users")],
        [InlineKeyboardButton("❌ Close Panel", callback_data="admin_close")]
    ]
    return InlineKeyboardMarkup(keyboard)

# /start Command Handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user(user)

    if user.id != ADMIN_ID:
        alert_msg = (
            f"🔔 **নতুন ইউজার বট চালু করেছেন!**\n\n"
            f"👤 নাম: {user.full_name}\n"
            f"🆔 ID: `{user.id}`\n"
            f"🏷️ Username: @{user.username if user.username else 'N/A'}"
        )
        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text=alert_msg, parse_mode="Markdown")
        except Exception:
            pass

    welcome_msg = f"হ্যালো {user.first_name}! 👋\nআমাদের সম্পূর্ণ অটোমেটিক শপ বটে আপনাকে স্বাগতম।"
    await update.message.reply_text(welcome_msg, reply_markup=get_main_keyboard(user.id))

# Text & Options Handler
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    register_user(user)

    state = context.user_data.get("state")

    # --- Admin States Handlers ---
    if state == "WAITING_PRODUCT_DETAILS" and user.id == ADMIN_ID:
        try:
            p_name, p_price = text.split("-")
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO products (name, price) VALUES (?, ?)", (p_name.strip(), float(p_price.strip())))
            conn.commit()
            conn.close()
            await update.message.reply_text("✅ নতুন প্রোডাক্ট সফলভাবে ডাটাবেজে যোগ করা হয়েছে!")
            context.user_data["state"] = None
        except Exception:
            await update.message.reply_text("❌ ফরম্যাট ভুল! দয়া করে লিখুন: `Name - Price` (যেমন: Netflix - 150)")
        return

    if state == "WAITING_STOCK_DETAILS" and user.id == ADMIN_ID:
        try:
            p_id, stock_code = text.split("-", 1)
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO stocks (product_id, item_data) VALUES (?, ?)", (int(p_id.strip()), stock_code.strip()))
            conn.commit()
            conn.close()
            await update.message.reply_text("✅ স্টকে নতুন আইটেম/কোড যোগ করা হয়েছে!")
            context.user_data["state"] = None
        except Exception:
            await update.message.reply_text("❌ ফরম্যাট ভুল! দয়া করে লিখুন: `ProductID - CodeOrAccountData` (যেমন: 1 - user:pass123)")
        return

    if state == "WAITING_BALANCE_DETAILS" and user.id == ADMIN_ID:
        try:
            target_id, amount = text.split("-")
            target_id = int(target_id.strip())
            amount = float(amount.strip())

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, target_id))
            conn.commit()
            conn.close()

            await update.message.reply_text(f"✅ ইউজার `{target_id}` এর অ্যাকাউন্টে {amount} BDT ব্যালেন্স যোগ করা হয়েছে।", parse_mode="Markdown")
            try:
                await context.bot.send_message(chat_id=target_id, text=f"🎉 আপনার অ্যাকাউন্টে {amount} BDT সফলভাবে যোগ করা হয়েছে!")
            except Exception:
                pass
            context.user_data["state"] = None
        except Exception:
            await update.message.reply_text("❌ ফরম্যাট ভুল! দয়া করে লিখুন: `UserID - Amount` (যেমন: 7523903272 - 500)")
        return

    # --- User Menu Buttons ---
    if text == "🛒 Buy Products":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT product_id, name, price FROM products")
        products = cursor.fetchall()
        conn.close()

        if not products:
            await update.message.reply_text("🛍️ বর্তমানে কোনো প্রোডাক্ট স্টকে এভেলেবল নেই।")
            return

        buttons = []
        for p_id, p_name, p_price in products:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM stocks WHERE product_id = ?", (p_id,))
            stock_count = cursor.fetchone()[0]
            conn.close()

            buttons.append([InlineKeyboardButton(f"{p_name} ({p_price} BDT) [ID: {p_id} | Stock: {stock_count}]", callback_data=f"buy_{p_id}")])

        await update.message.reply_text("🛍️ **আমাদের সব উপলব্ধ প্রোডাক্ট তালিকা:**", reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

    elif text == "💰 Add Balance":
        deposit_msg = (
            f"💰 **অ্যাকাউন্টে ব্যালেন্স যোগ করুন**\n\n"
            f"নিচের যেকোনো মাধ্যমে **Send Money** করুন:\n\n"
            f"🩷 **বিকাশ (Bkash):** `{DEPOSIT_NUMBER}` (Personal)\n"
            f"❤️ **নগদ (Nagad):** `{DEPOSIT_NUMBER}` (Personal)\n"
            f"💜 **রকেট (Rocket):** `{DEPOSIT_NUMBER}` (Personal)\n\n"
            f"⚠️ টাকা পাঠানোর পর আপনার **TrxID** এবং **ইউজার আইডি** (`{user.id}`) লিখে নিচে মেসেজ পাঠিয়ে দিন।\n"
            f"অথবা সরাসরি এডমিনকে জানান: {ADMIN_USERNAME}"
        )
        await update.message.reply_text(deposit_msg, parse_mode="Markdown")

    elif text == "💳 My Balance":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user.id,))
        row = cursor.fetchone()
        conn.close()
        bal = row[0] if row else 0.0
        await update.message.reply_text(f"💳 **আপনার বর্তমান ব্যালেন্স:** {bal} BDT")

    elif text == "📦 My Orders":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT item_name, item_data, price, date FROM orders WHERE user_id = ?", (user.id,))
        orders = cursor.fetchall()
        conn.close()

        if not orders:
            await update.message.reply_text("📦 আপনি এখনও কোনো প্রোডাক্ট কেনেননি।")
        else:
            msg = "📦 **আপনার কেনা প্রোডাক্টসমূহ:**\n\n"
            for name, data, price, dt in orders:
                msg += f"• **{name}** ({price} BDT)\n  🔑 `Data/Code:` `{data}`\n  🗓️ `{dt}`\n\n"
            await update.message.reply_text(msg, parse_mode="Markdown")

    elif text == "🎧 Support":
        support_text = (
            f"🎧 **সাপোর্ট সেন্টার**\n\n"
            f"যেকোনো বিষয়ে সহযোগিতার জন্য যোগাযোগ করুন:\n"
            f"👨‍💻 এডমিন: {ADMIN_USERNAME}\n"
            f"🆔 ID: `{ADMIN_ID}`"
        )
        await update.message.reply_text(support_text, parse_mode="Markdown")

    elif text == "⚙️ Admin Control Panel" and user.id == ADMIN_ID:
        await update.message.reply_text("🛠️ **এডমিন কন্ট্রোল প্যানেল:**", reply_markup=get_admin_keyboard())

    else:
        if user.id != ADMIN_ID:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT username FROM users WHERE user_id = ?", (user.id,))
            uname_row = cursor.fetchone()
            conn.close()
            username_str = uname_row[0] if uname_row else "N/A"

            to_admin = (
                f"📩 **ইউজারের বার্তা / TrxID:**\n"
                f"👤 নাম: {user.full_name}\n"
                f"🏷️ ইউজারনেম: {username_str}\n"
                f"🆔 ID: `{user.id}`\n\n"
                f"💬 **মেসেজ:** {text}"
            )
            await context.bot.send_message(chat_id=ADMIN_ID, text=to_admin, parse_mode="Markdown")
            await update.message.reply_text("✅ আপনার মেসেজ বা TrxID এডমিনের কাছে পাঠানো হয়েছে। খুব শীঘ্রই ব্যালেন্স ভেরিফাই করা হবে।")

# Callback Query Handler
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    data = query.data
    await query.answer()

    if data.startswith("buy_"):
        p_id = int(data.split("_")[1])
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT name, price FROM products WHERE product_id = ?", (p_id,))
        product = cursor.fetchone()

        if product:
            p_name, p_price = product
            cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user.id,))
            user_bal = cursor.fetchone()[0]

            if user_bal >= p_price:
                cursor.execute("SELECT stock_id, item_data FROM stocks WHERE product_id = ? LIMIT 1", (p_id,))
                stock = cursor.fetchone()

                if stock:
                    stock_id, item_data = stock
                    
                    cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (p_price, user.id))
                    cursor.execute("DELETE FROM stocks WHERE stock_id = ?", (stock_id,))
                    cursor.execute("INSERT INTO orders (user_id, item_name, item_data, price) VALUES (?, ?, ?, ?)",
                                   (user.id, p_name, item_data, p_price))
                    conn.commit()

                    await query.edit_message_text(
                        f"✅ **অর্ডার সফল ও অটোমেটিক ডেলিভারি সম্পন্ন!**\n\n"
                        f"🛍️ প্রোডাক্ট: `{p_name}`\n"
                        f"🔑 **আপনার সার্ভিস কোড / অ্যাকাউন্ট ডিটেইলস:**\n`{item_data}`\n\n"
                        f"💳 অবশিষ্ঠ ব্যালেন্স: {user_bal - p_price} BDT",
                        parse_mode="Markdown"
                    )

                    admin_alert = (
                        f"🛒 **অটো ডেলিভারি সম্পন্ন হয়েছে!**\n\n"
                        f"👤 ইউজার: {user.full_name}\n"
                        f"🆔 ID: `{user.id}`\n"
                        f"🛍️ প্রোডাক্ট: {p_name}\n"
                        f"💰 মূল্যে: {p_price} BDT"
                    )
                    await context.bot.send_message(chat_id=ADMIN_ID, text=admin_alert, parse_mode="Markdown")

                else:
                    await query.edit_message_text("❌ দুঃখিত! এই মুহূর্তে এই প্রোডাক্টের স্টক খালি রয়েছে।")
            else:
                await query.edit_message_text(f"❌ **অপর্যাপ্ত ব্যালেন্স!**\nপ্রয়োজন: {p_price} BDT। আপনার আছে: {user_bal} BDT।")

        conn.close()

    if user.id == ADMIN_ID:
        if data == "admin_add_prod":
            context.user_data["state"] = "WAITING_PRODUCT_DETAILS"
            await query.edit_message_text("📝 লিখুন: `প্রোডাক্ট নাম - দাম`\n\nউদাহরণ: `Netflix 1 Month - 150`", parse_mode="Markdown")

        elif data == "admin_add_stock":
            context.user_data["state"] = "WAITING_STOCK_DETAILS"
            await query.edit_message_text("📦 লিখুন: `ProductID - CodeOrAccountData`\n\nউদাহরণ: `1 - netflix_user:pass123`", parse_mode="Markdown")

        elif data == "admin_add_bal":
            context.user_data["state"] = "WAITING_BALANCE_DETAILS"
            await query.edit_message_text("💳 লিখুন: `UserID - Amount`\n\nউদাহরণ: `7523903272 - 500`", parse_mode="Markdown")

        elif data == "admin_view_users":
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, full_name, username, balance FROM users")
            users = cursor.fetchall()
4            conn.close()

            msg = "👥 **ইউজার তালিকা:**\n\n"
            for u_id, name, uname, bal in users:
                msg += f"• {name} ({uname}) | ID: `{u_id}` | Bal: {bal} BDT\n"
            await query.edit_message_text(msg, parse_mode="Markdown")

        elif data == "admin_close":
            await query.edit_message_text("❌ এডমিন প্যানেল বন্ধ করা হয়েছে।")

# Application Execution
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("🤖 সম্পূর্ণ অটোমেটিক শপ বট সফলভাবে রান হচ্ছে...")
    app.run_polling()
