# main.py (รวมโค้ดและปรับปรุงล่าสุด - เน้นการลบข้อความคำสั่ง)

import discord
from discord.ext import commands, tasks
import asyncio
from datetime import datetime
import pytz
import json
import os
from dotenv import load_dotenv

# --- ส่วนของ Flask Server ---
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Server is running!"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    # ในการ deploy จริง ควรให้ Werkzeug (Flask's default server) แสดง log น้อยลง
    # หรือใช้ production-ready WSGI server เช่น gunicorn
    print(f"Flask server attempting to run on host 0.0.0.0, port {port}")
    try:
        app.run(host='0.0.0.0', port=port)
    except Exception as e_flask_run:
        print(f"!!! ERROR starting Flask server: {e_flask_run}")


def start_server():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    print("Flask server thread initiated.")

# --- จบส่วนของ Flask Server ---

load_dotenv() # โหลดค่าจาก .env

# --- การตั้งค่า Bot ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True # จำเป็นถ้าจะใช้ ctx.author.name หรือเกี่ยวกับ members
bot = commands.Bot(command_prefix='!', intents=intents)
TZ_BANGKOK = pytz.timezone('Asia/Bangkok')

# --- ข้อมูลหลักของระบบ ---
members = { # ควรโหลดจาก config หรือ database ในอนาคตถ้ามีการเปลี่ยนแปลงบ่อย
    "Juno": "ขาด", "candy": "ขาด", "sindrea": "ขาด",
    "yam": "ขาด", "chababa": "ขาด", "naila": "ขาด",
}
name_mapping = { # ควรโหลดจาก config หรือ database เช่นกัน
    "onitsuka3819": "Juno", "candy_dayy": "candy", "sindrea_cz": "sindrea",
    "yam2196": "yam", "chababa.": "chababa", "naila_888": "naila",
}
# ตัวแปร global สำหรับการซ้อมปัจจุบัน
practice_info = {
    "id": None, "date": None, "time": None, "location": None,
    "is_open_for_signup": False
}
practice_history = [] # เก็บประวัติการซ้อมทั้งหมด
last_practice_message = None # เก็บ object ข้อความล่าสุดที่ส่งไปห้องประกาศ
update_enabled = True # ควบคุมการทำงานของ tasks.loop

# --- ค่าคงที่ ---
HISTORY_FILE = 'practice_history.json' # ชื่อไฟล์สำหรับเก็บข้อมูล
ANNOUNCEMENT_CHANNEL_ID = 1375796432140763216 # ID ห้องประกาศ (สำคัญมาก)
SETTING_CHANNEL_NAME = "🔥┃setting"
SIGNUP_CHANNEL_NAME = "🔥┃ลงชื่อซ้อม"

# --- ฟังก์ชันจัดการข้อมูล ---
def log_ts(message): # ฟังก์ชันช่วย log พร้อม timestamp
    print(f"[{datetime.now(TZ_BANGKOK).strftime('%Y-%m-%d %H:%M:%S')}] {message}")

def load_data_from_file(): # เปลี่ยนชื่อให้สื่อถึงการโหลดข้อมูลทั้งหมด
    global practice_history, update_enabled, practice_info
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        practice_history = data.get("history", [])
        update_enabled = data.get("update_enabled", True)
        # รีเซ็ต practice_info ทุกครั้งที่โหลด; การซ้อมปัจจุบันจะถูกตั้งด้วย !setplay เท่านั้น
        practice_info = {"id": None, "date": None, "time": None, "location": None, "is_open_for_signup": False}

        # ตรวจสอบและซ่อมแซม ID และ is_open_for_signup ใน history
        history_modified = False
        for i, entry in enumerate(practice_history):
            if not entry.get("id") or not entry["id"].isdigit():
                entry["id"] = f"{len(practice_history) - i:03d}" # Logic สร้าง ID ชั่วคราว
                history_modified = True
            if "is_open_for_signup" not in entry:
                entry["is_open_for_signup"] = False # สมมติว่า entry เก่าๆ ปิดรับไปแล้ว
                history_modified = True
        if history_modified:
            save_data_to_file()
        log_ts(f"Data loaded. History entries: {len(practice_history)}, Update enabled: {update_enabled}")
    except FileNotFoundError:
        log_ts(f"'{HISTORY_FILE}' not found. Initializing with empty data.")
        practice_history, update_enabled = [], True
        practice_info = {"id": None, "date": None, "time": None, "location": None, "is_open_for_signup": False}
        save_data_to_file() # สร้างไฟล์ใหม่ถ้ายังไม่มี
    except json.JSONDecodeError:
        log_ts(f"Error decoding '{HISTORY_FILE}'. File might be corrupted. Initializing.")
        practice_history, update_enabled = [], True
        practice_info = {"id": None, "date": None, "time": None, "location": None, "is_open_for_signup": False}
        # อาจจะมีการสำรองไฟล์เก่าก่อนเขียนทับ
    except Exception as e:
        log_ts(f"An unexpected error occurred during load_data_from_file: {e}")


def save_data_to_file(): # เปลี่ยนชื่อให้สื่อถึงการบันทึกข้อมูลทั้งหมด
    data_to_save = {"history": practice_history, "update_enabled": update_enabled}
    # ไม่ควรบันทึก practice_info ลงไฟล์ history หลัก เพราะมันคือ "สถานะปัจจุบัน"
    # ถ้าต้องการ persistence ของ practice_info ควรแยกไฟล์ หรือใช้ DB
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=4)
        # log_ts(f"Data saved to '{HISTORY_FILE}'.") # อาจจะ log ถี่ไป
    except Exception as e:
        log_ts(f"ERROR saving data to '{HISTORY_FILE}': {e}")

def generate_new_practice_id():
    if not practice_history: return "001"
    numeric_ids = [int(e["id"]) for e in practice_history if e.get("id") and e["id"].isdigit()]
    return f"{(max(numeric_ids) if numeric_ids else 0) + 1:03d}"

def archive_current_practice_if_exists():
    """บันทึกการซ้อมปัจจุบัน (practice_info) ลงใน practice_history ถ้ามีข้อมูล"""
    if practice_info.get("id") and all(practice_info.get(k) for k in ["date", "time", "location"]):
        # ตรวจสอบว่า ID นี้มีใน history หรือยัง
        existing_entry_index = -1
        for i, entry in enumerate(practice_history):
            if entry.get("id") == practice_info["id"]:
                existing_entry_index = i
                break
        
        entry_to_save = {
            "id": practice_info["id"],
            "date": practice_info["date"],
            "time": practice_info["time"],
            "location": practice_info["location"],
            "members": members.copy(), # ใช้ members ณ เวลาที่บันทึก
            "is_open_for_signup": practice_info.get("is_open_for_signup", False)
        }

        if existing_entry_index != -1: # ถ้ามี ID นี้อยู่แล้ว, ให้อัปเดต
            practice_history[existing_entry_index] = entry_to_save
            log_ts(f"Updated practice ID {practice_info['id']} in history.")
        else: # ถ้าเป็น ID ใหม่, ให้เพิ่มเข้าไป
            practice_history.append(entry_to_save)
            log_ts(f"Archived new practice ID {practice_info['id']} to history.")
        
        practice_history.sort(key=lambda x: x.get("id", "000"))
        save_data_to_file()


def create_practice_notification_embed(): # เปลี่ยนชื่อให้สื่อว่าสร้าง Embed
    if not all(practice_info.get(k) for k in ["id", "date", "time", "location"]):
        return None # ไม่มีข้อมูลการซ้อมปัจจุบัน

    embed = discord.Embed(
        title=f"📢 การซ้อม (ฉบับที่ {practice_info['id']})",
        color=discord.Color.blue() if practice_info.get("is_open_for_signup") else discord.Color.orange()
    )
    embed.add_field(name="📅 วันที่", value=practice_info['date'], inline=True)
    embed.add_field(name="⏰ เวลา", value=practice_info['time'], inline=True)
    embed.add_field(name="📍 สถานที่", value=practice_info['location'], inline=False)

    status_text = "✅ **เปิดรับลงชื่อ**" if practice_info.get("is_open_for_signup") else "🅾️ **ปิดรับลงชื่อแล้ว**"
    embed.add_field(name="สถานะการลงชื่อ", value=status_text, inline=False)

    member_status_lines = [f"• {name}: {status}" for name, status in members.items()]
    embed.add_field(name="📋 รายชื่อแก๊ง", value="\n".join(member_status_lines) or "ไม่มีข้อมูลสมาชิก", inline=False)
    embed.set_footer(text=f"อัปเดตเมื่อ: {datetime.now(TZ_BANGKOK).strftime('%H:%M:%S')}")
    return embed

def create_practice_summary_embed(practice_id_to_summarize: str): # เปลี่ยนชื่อ
    data_source = None
    current_members_state = None

    if practice_info.get("id") == practice_id_to_summarize:
        data_source = practice_info
        current_members_state = members # สรุปการซ้อมปัจจุบัน ใช้สถานะ members ปัจจุบัน
    else:
        for entry in practice_history:
            if entry.get("id") == practice_id_to_summarize:
                data_source = entry
                current_members_state = entry.get("members", {}) # สรุปจาก history ใช้ members ที่บันทึกไว้
                break
    
    if not data_source or not all(data_source.get(k) for k in ["date", "time", "location"]):
        return discord.Embed(title=f"ไม่พบข้อมูลการซ้อม", description=f"ไม่พบข้อมูลสำหรับฉบับที่ {practice_id_to_summarize}", color=discord.Color.red())

    embed = discord.Embed(title=f"📊 สรุปการซ้อม (ฉบับที่ {practice_id_to_summarize})", color=discord.Color.green())
    embed.add_field(name="📅 วันที่", value=data_source['date'], inline=True)
    embed.add_field(name="⏰ เวลา", value=data_source['time'], inline=True)
    embed.add_field(name="📍 สถานที่", value=data_source['location'], inline=False)
    
    member_summary_lines = [f"• {name}: {status}" for name, status in current_members_state.items()]
    embed.add_field(name="📋 ผลการลงชื่อ", value="\n".join(member_summary_lines) or "ไม่มีข้อมูลการลงชื่อ", inline=False)
    embed.set_footer(text=f"ข้อมูลสรุป ณ {datetime.now(TZ_BANGKOK).strftime('%d/%m/%Y %H:%M:%S')}")
    return embed

# --- Tasks ---
@tasks.loop(minutes=5)
async def periodic_status_update_task(): # เปลี่ยนชื่อ
    global last_practice_message
    if not update_enabled or not practice_info.get("id") or not bot.is_ready():
        return

    announcement_ch = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
    if not announcement_ch:
        log_ts(f"ERROR: Announcement channel ID {ANNOUNCEMENT_CHANNEL_ID} not found for periodic update.")
        return

    if last_practice_message:
        try:
            await last_practice_message.delete()
        except (discord.NotFound, discord.Forbidden): pass # Already deleted or no permission
        except Exception as e: log_ts(f"Error deleting old status message for update: {e}")
        finally: last_practice_message = None

    notification_embed = create_practice_notification_embed()
    if notification_embed:
        try:
            last_practice_message = await announcement_ch.send(embed=notification_embed)
        except discord.Forbidden: log_ts(f"ERROR: Bot lacks permission to send messages in announcement channel for update.")
        except Exception as e: log_ts(f"Error sending new status message for update: {e}")

# --- Bot Events ---
@bot.event
async def on_ready():
    log_ts(f"Bot {bot.user.name} (ID: {bot.user.id}) is online and ready!")
    load_data_from_file() # โหลดข้อมูลทั้งหมดเมื่อบอทพร้อม
    if not periodic_status_update_task.is_running():
        periodic_status_update_task.start()
        log_ts("Periodic status update task started.")
    start_server() # เริ่ม Flask server
    try:
        activity_name = f"ดูแลการซ้อม | {bot.command_prefix}setplay"
        await bot.change_presence(activity=discord.Game(name=activity_name))
        log_ts(f"Bot presence set to: Playing {activity_name}")
    except Exception as e:
        log_ts(f"Error setting bot presence: {e}")

# --- Decorators & Checks ---
def is_correct_channel(channel_name_or_id): # เปลี่ยนชื่อ
    async def predicate(ctx):
        is_valid = False
        if isinstance(channel_name_or_id, int):
            is_valid = (ctx.channel.id == channel_name_or_id)
        elif isinstance(channel_name_or_id, str):
            is_valid = (ctx.channel.name.lower() == channel_name_or_id.lower())
        
        if not is_valid:
            error_msg = f"คำสั่งนี้ใช้ได้เฉพาะในห้อง '{channel_name_or_id}' เท่านั้น!" if isinstance(channel_name_or_id, str) else "คำสั่งนี้ใช้ได้เฉพาะในห้องที่กำหนดเท่านั้น!"
            try: await ctx.send(error_msg, ephemeral=True, delete_after=10)
            except: pass # Ignore if cannot send ephemeral (e.g., in DMs, though check should prevent this)
        return is_valid
    return commands.check(predicate)

# --- Bot Commands ---
@bot.command(name="ปิดอัปเดต", aliases=["disableupdate"])
@is_correct_channel(SETTING_CHANNEL_NAME)
@commands.has_permissions(administrator=True) # เพิ่มการตรวจสอบสิทธิ์
async def disable_periodic_update(ctx):
    global update_enabled
    if not update_enabled:
        await ctx.send("การอัปเดตสถานะอัตโนมัติปิดอยู่แล้ว", ephemeral=True, delete_after=10)
        return
    update_enabled = False
    save_data_to_file() # บันทึกสถานะ update_enabled
    await ctx.send("✅ ปิดการอัปเดตสถานะอัตโนมัติทุก 5 นาทีแล้ว", ephemeral=True)

@bot.command(name="เปิดอัปเดต", aliases=["enableupdate"])
@is_correct_channel(SETTING_CHANNEL_NAME)
@commands.has_permissions(administrator=True) # เพิ่มการตรวจสอบสิทธิ์
async def enable_periodic_update(ctx):
    global update_enabled, last_practice_message
    if update_enabled:
        await ctx.send("การอัปเดตสถานะอัตโนมัติเปิดอยู่แล้ว", ephemeral=True, delete_after=10)
        return
    update_enabled = True
    save_data_to_file() # บันทึกสถานะ update_enabled
    await ctx.send("✅ เปิดการอัปเดตสถานะอัตโนมัติทุก 5 นาทีแล้ว", ephemeral=True)
    # ลองอัปเดตทันที
    if practice_info.get("id"):
        announcement_ch = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
        if announcement_ch:
            if last_practice_message:
                try: await last_practice_message.delete()
                except: pass
            notification_embed = create_practice_notification_embed()
            if notification_embed:
                try: last_practice_message = await announcement_ch.send(embed=notification_embed)
                except: pass

@bot.command(name="ลงชื่อซ้อม", aliases=["ซ้อมทีม"])
@is_correct_channel(SIGNUP_CHANNEL_NAME)
async def sign_up_for_practice(ctx): # เปลี่ยนชื่อฟังก์ชัน
    command_message_to_delete = ctx.message # เก็บข้อความคำสั่งไว้ก่อน

    if not practice_info.get("id"):
        await ctx.send("⚠️ ยังไม่มีการตั้งค่าการซ้อมในขณะนี้", ephemeral=True, delete_after=10)
        try: await command_message_to_delete.delete(delay=1) # ลบหลังจากส่ง feedback
        except: pass
        return
        
    if not practice_info.get("is_open_for_signup", False):
        await ctx.send(f"🅾️ การซ้อม (ฉบับที่ {practice_info['id']}) ปิดรับการลงชื่อแล้ว", ephemeral=True, delete_after=10)
        try: await command_message_to_delete.delete(delay=1)
        except: pass
        return

    discord_user_name_key = ctx.author.name # หรือ ctx.author.display_name หรือ ctx.author.global_name
    mapped_name = name_mapping.get(discord_user_name_key)

    if mapped_name and mapped_name in members:
        if members[mapped_name] == "มาแล้ว":
            await ctx.send(f"✅ {mapped_name} ได้ลงชื่อไปแล้ว", ephemeral=True, delete_after=7)
        else:
            members[mapped_name] = "มาแล้ว"
            await ctx.send(f"👍 {mapped_name} ลงชื่อซ้อมเรียบร้อย!", delete_after=7) # แจ้งผู้ใช้ก่อน
            archive_current_practice_if_exists() # อัปเดตข้อมูลการซ้อมปัจจุบันใน history/file

            # อัปเดตข้อความในห้องประกาศ (ถ้ายังเปิด update_enabled)
            if update_enabled:
                global last_practice_message
                announcement_ch = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
                if announcement_ch:
                    if last_practice_message:
                        try: await last_practice_message.delete()
                        except: pass
                    notification_embed = create_practice_notification_embed()
                    if notification_embed:
                        try: last_practice_message = await announcement_ch.send(embed=notification_embed)
                        except: pass
    else:
        await ctx.send(f"❓ ไม่พบชื่อคุณ ({discord_user_name_key}) ในระบบลงทะเบียน", ephemeral=True, delete_after=10)

    # ลบข้อความคำสั่งของผู้ใช้ในทุกกรณี (ถ้าบอทมีสิทธิ์)
    try:
        await command_message_to_delete.delete()
    except discord.Forbidden:
        log_ts(f"Bot lacks 'Manage Messages' permission in '{ctx.channel.name}' to delete user command.")
    except discord.HTTPException:
        pass # Message might have been deleted already

@bot.command(name="เช็คสถานะ", aliases=["สถานะซ้อม"])
async def check_current_practice_status(ctx): # เปลี่ยนชื่อ
    if not practice_info.get("id"):
        await ctx.send("ยังไม่มีการตั้งค่าการซ้อมปัจจุบัน", ephemeral=True, delete_after=10)
        return
    notification_embed = create_practice_notification_embed()
    if notification_embed:
        await ctx.send(embed=notification_embed)
    else:
        await ctx.send("เกิดข้อผิดพลาดในการสร้างข้อความสถานะ", ephemeral=True, delete_after=10)

@bot.command(name="ตั้งค่าซ้อม", aliases=["setplay"])
@is_correct_channel(SETTING_CHANNEL_NAME)
@commands.has_permissions(manage_guild=True) # หรือ role ที่เหมาะสม
async def setup_new_practice(ctx): # เปลี่ยนชื่อ
    # 1. บันทึกการซ้อมปัจจุบัน (ถ้ามี) ลง history และถือว่ามันจบไปแล้ว
    if practice_info.get("id"):
        if practice_info.get("is_open_for_signup"): # ถ้าอันเก่ายังเปิดอยู่ ให้ปิดก่อน
            practice_info["is_open_for_signup"] = False
        archive_current_practice_if_exists() # บันทึกอันเก่า

    # 2. เตรียมรับข้อมูลใหม่
    def message_check(m): return m.author == ctx.author and m.channel == ctx.channel

    inputs_required = [
        ("วันที่ซ้อม (YYYY-MM-DD):", '%Y-%m-%d', "date"),
        ("เวลาซ้อม (HH:MM):", '%H:%M', "time"),
        ("สถานที่ซ้อม:", None, "location") # None for no format check beyond stripping
    ]
    new_practice_data = {}
    await ctx.send("✍️ กรุณาใส่ข้อมูลการซ้อมใหม่ (ตอบทีละรายการ):")

    for prompt, fmt, key in inputs_required:
        await ctx.send(prompt)
        try:
            msg = await bot.wait_for('message', check=message_check, timeout=120.0)
            content = msg.content.strip()
            if fmt: # ถ้ามีการตรวจสอบ format (date, time)
                datetime.strptime(content, fmt) # ลองแปลง, ถ้า error จะไปที่ except ValueError
            if not content: # ป้องกันการป้อนค่าว่าง
                await ctx.send("⚠️ ข้อมูลป้อนเข้าไม่ควรเป็นค่าว่าง กรุณาเริ่มใหม่ด้วย `!setplay`", ephemeral=True)
                return
            new_practice_data[key] = content
        except ValueError:
            await ctx.send(f"⚠️ รูปแบบข้อมูลสำหรับ '{key}' ไม่ถูกต้อง (ตัวอย่าง: {prompt.split('(')[1].split(')')[0]}). กรุณาเริ่มใหม่ด้วย `!setplay`", ephemeral=True)
            return
        except asyncio.TimeoutError:
            await ctx.send("⏰ หมดเวลาการป้อนข้อมูล กรุณาเริ่มใหม่ด้วย `!setplay`", ephemeral=True)
            return

    # 3. อัปเดต practice_info ด้วยข้อมูลใหม่
    practice_info["id"] = generate_new_practice_id()
    practice_info["date"] = new_practice_data["date"]
    practice_info["time"] = new_practice_data["time"]
    practice_info["location"] = new_practice_data["location"]
    practice_info["is_open_for_signup"] = True # เปิดรับลงชื่อสำหรับการซ้อมใหม่

    # 4. รีเซ็ตสถานะสมาชิกสำหรับ `members` ปัจจุบัน
    for member_name in members: members[member_name] = "ขาด"

    # 5. บันทึกการซ้อมใหม่นี้ลง history ทันที (สถานะ "เปิด")
    archive_current_practice_if_exists()
    await ctx.send(f"✅ ตั้งค่าการซ้อมใหม่ (ฉบับที่ {practice_info['id']}) เรียบร้อยแล้ว!", ephemeral=True)

    # 6. ส่ง Notification ไปยังห้องประกาศ
    global last_practice_message
    announcement_ch = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
    if announcement_ch:
        if last_practice_message:
            try: await last_practice_message.delete()
            except: pass
        notification_embed = create_practice_notification_embed()
        if notification_embed:
            try: last_practice_message = await announcement_ch.send(embed=notification_embed)
            except discord.Forbidden: log_ts(f"ERROR: Bot lacks permission to send to announcement channel for new practice.")
    else:
        log_ts(f"ERROR: Announcement channel ID {ANNOUNCEMENT_CHANNEL_ID} not found for new practice notification.")


@bot.command(name="สรุปผล", aliases=["สรุป"])
@is_correct_channel(SETTING_CHANNEL_NAME)
@commands.has_permissions(manage_guild=True) # หรือ role ที่เหมาะสม
async def summarize_practice(ctx, practice_id_to_summarize: str): # เปลี่ยนชื่อ
    if not (practice_id_to_summarize.isdigit() and len(practice_id_to_summarize) == 3):
        await ctx.send("⚠️ ID การซ้อมต้องเป็นตัวเลข 3 หลัก (เช่น 001)", ephemeral=True, delete_after=10)
        return

    feedback_message = [] # เก็บข้อความ feedback

    # ถ้าเป็นการสรุปการซ้อม "ปัจจุบัน" ให้ปิดการลงชื่อ
    if practice_info.get("id") == practice_id_to_summarize:
        if practice_info.get("is_open_for_signup"):
            practice_info["is_open_for_signup"] = False
            archive_current_practice_if_exists() # บันทึกการเปลี่ยนแปลงนี้
            feedback_message.append(f"การซ้อมปัจจุบัน (ฉบับที่ {practice_id_to_summarize}) ได้ปิดรับการลงชื่อแล้ว")
        else:
            feedback_message.append(f"การซ้อมปัจจุบัน (ฉบับที่ {practice_id_to_summarize}) ปิดรับการลงชื่อไปแล้วก่อนหน้านี้")
    
    announcement_ch = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
    if not announcement_ch:
        await ctx.send(f"❌ ไม่พบห้องประกาศ (ID: {ANNOUNCEMENT_CHANNEL_ID}) ไม่สามารถส่งสรุปได้", ephemeral=True)
        return

    summary_embed = create_practice_summary_embed(practice_id_to_summarize)
    
    try:
        await announcement_ch.send(embed=summary_embed)
        feedback_message.append(f"📊 สรุปการซ้อม (ฉบับที่ {practice_id_to_summarize}) ถูกส่งไปยังห้องประกาศแล้ว!")
    except discord.Forbidden:
        feedback_message.append(f"⚠️ สามารถสร้างสรุป (ฉบับที่ {practice_id_to_summarize}) ได้ แต่บอทไม่มีสิทธิ์ส่งข้อความไปยังห้องประกาศ")
    except Exception as e:
        feedback_message.append(f"❌ เกิดข้อผิดพลาดในการส่งสรุป: {e}")
        log_ts(f"Error sending summary: {e}")

    if feedback_message:
        await ctx.send("\n".join(feedback_message), ephemeral=True, delete_after=15)


# --- Error Handling ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return # ไม่ต้องทำอะไรถ้าหาคำสั่งไม่เจอ
    elif isinstance(error, commands.CheckFailure): # รวมถึง is_correct_channel และ has_permissions
        # ข้อความ error จะถูกส่งจากตัว check เองแล้ว (ephemeral)
        log_ts(f"CheckFailure by {ctx.author} for command {ctx.command}: {error}")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"⚠️ คุณลืมใส่ข้อมูลบางอย่างสำหรับคำสั่งนี้ กรุณาดูวิธีใช้: `{ctx.prefix}{ctx.command.name} {ctx.command.signature}`", ephemeral=True, delete_after=15)
    else:
        log_ts(f"Unhandled error in command '{ctx.command}' by '{ctx.author}': {error}")
        traceback_str = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        log_ts(f"Traceback:\n{traceback_str}")
        try:
            await ctx.send(f"เกิดข้อผิดพลาดที่ไม่คาดคิดขณะประมวลผลคำสั่ง: `{error}`", ephemeral=True, delete_after=15)
        except: pass


# --- Run Bot ---
BOT_TOKEN_ENV = os.getenv('DISCORD_TOKEN')
if not BOT_TOKEN_ENV:
    log_ts("CRITICAL ERROR: DISCORD_TOKEN environment variable not found. Bot cannot start.")
else:
    try:
        log_ts("Attempting to run bot...")
        bot.run(BOT_TOKEN_ENV)
    except discord.errors.LoginFailure:
        log_ts("CRITICAL ERROR: Login Failed. Token is invalid or bot has incorrect intents enabled.")
    except discord.errors.PrivilegedIntentsRequired:
        log_ts("CRITICAL ERROR: Privileged Intents (Server Members or Message Content) are not enabled in the Discord Developer Portal for this bot.")
    except Exception as e:
        log_ts(f"CRITICAL ERROR during bot.run(): {e}")
        traceback.print_exc()