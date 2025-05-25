# main.py (รวมโค้ดและปรับปรุงล่าสุด)

import discord
from discord.ext import commands, tasks
import asyncio
from datetime import datetime
import pytz
import json
import os
from dotenv import load_dotenv # เพิ่มเข้ามา

# --- ส่วนของ Flask Server ---
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Server is running!"

def run_flask():
    # อ่านค่า PORT จาก environment variable, ถ้าไม่มีให้ใช้ 8080 เป็น default
    port = int(os.environ.get('PORT', 8080)) # แก้ไข port ตรงนี้ให้ใช้จาก env
    app.run(host='0.0.0.0', port=port) # แก้ไข port ตรงนี้ให้ใช้จาก env

def start_server():
    t = Thread(target=run_flask)
    t.daemon = True # ตั้งค่าให้ thread นี้ปิดตัวลงเมื่อ main program ปิด
    t.start()

# --- จบส่วนของ Flask Server ---

# โหลดค่าจากไฟล์ .env เข้าสู่ environment variables
load_dotenv()

# ตั้งค่า bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

# กำหนดเขตเวลา +07 (ประเทศไทย)
tz = pytz.timezone('Asia/Bangkok')

# รายชื่อสมาชิกและสถานะเริ่มต้น
members = {
    "Juno": "ขาด",
    "Candy": "ขาด",
    "Sindrea": "ขาด",
    "Yam": "ขาด",
    "Chababa": "ขาด",
    "Naila": "ขาด",
    "HoneyLex": "ขาด",
    "Hanna": "ขาด",
    "HeiHei": "ขาด",
    "Songkran": "ขาด",
    "Aiikz": "ขาด",
}

# ผูกชื่อ Discord กับชื่อในรายการ
name_mapping = {
    "onitsuka3819": "Juno",
    "candy_dayy": "Candy",
    "sindrea_cz": "Sindrea",
    "yam2196": "Yam",
    "chababa.": "Chababa",
    "naila_888": "Naila",
    "honeylexfahwabwab": "HoneyLex",
    "hanna05682": "Hanna",
    "ms.k3144": "HeiHei",
    "songkran_gbn": "Songkran",
    "aiikz": "Aiikz",

}

# ตัวแปรเก็บข้อมูลการซ้อมปัจจุบัน
practice_info = {
    "id": None,
    "date": None,
    "time": None,
    "location": None,
    "is_open_for_signup": False # <<<< แก้ไข: เพิ่มสถานะการเปิดรับลงชื่อ
}

# ตัวแปรเก็บประวัติการซ้อม
practice_history = []

# ตัวแปรเก็บข้อความล่าสุดของการซ้อมปัจจุบันในห้องประกาศ
last_practice_message = None

# ตัวแปรควบคุมการอัปเดตสถานะ
update_enabled = True

# ไอดีห้อง
ANNOUNCEMENT_CHANNEL_ID = 1375796432140763216 # ใส่ ID ห้องประกาศจริง
SETTING_CHANNEL_NAME = "🔥┃setting" # ชื่อห้อง setting
SIGNUP_CHANNEL_NAME = "🔥┃ลงชื่อซ้อม" # ชื่อห้องลงชื่อซ้อม

# ฟังก์ชันโหลดประวัติและการตั้งค่าจากไฟล์
def load_history_from_file():
    global practice_history, update_enabled, practice_info
    try:
        with open('practice_history.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            practice_history = data.get("history", [])
            update_enabled = data.get("update_enabled", True)
            # หากต้องการโหลด practice_info ล่าสุดจากไฟล์ (ถ้ามีการบันทึก)
            # current_practice_from_file = data.get("current_practice", None)
            # if current_practice_from_file:
            #     practice_info = current_practice_from_file
            # else: # รีเซ็ตถ้าไม่มีข้อมูลปัจจุบันในไฟล์
            practice_info = {
                "id": None, "date": None, "time": None, "location": None,
                "is_open_for_signup": False
            }

        # ตรวจสอบและเพิ่ม ID ให้ข้อมูลเก่า (ถ้าจำเป็น)
        id_changed = False
        for i, entry in enumerate(practice_history):
            if "id" not in entry or not entry["id"]:
                entry["id"] = f"{len(practice_history) - i:03d}" # หรือ logic การสร้าง ID อื่นๆ
                id_changed = True
            # เพิ่ม is_open_for_signup ถ้าไม่มีในข้อมูลเก่า (ถือว่าปิดไปแล้ว)
            if "is_open_for_signup" not in entry:
                entry["is_open_for_signup"] = False # ข้อมูลเก่าถือว่าปิดรับแล้ว
                id_changed = True # ตั้งเป็น True เพื่อให้มีการ save_history_to_file()

        if id_changed:
            save_history_to_file()

    except FileNotFoundError:
        practice_history = []
        update_enabled = True
        practice_info = {
            "id": None, "date": None, "time": None, "location": None,
            "is_open_for_signup": False
        }
    except json.JSONDecodeError:
        print("Error decoding practice_history.json. File might be corrupted or empty.")
        practice_history = []
        update_enabled = True
        practice_info = {
            "id": None, "date": None, "time": None, "location": None,
            "is_open_for_signup": False
        }

# ฟังก์ชันบันทึกประวัติและการตั้งค่าลงไฟล์
def save_history_to_file():
    data = {
        "history": practice_history,
        "update_enabled": update_enabled
        # หากต้องการบันทึก practice_info ปัจจุบันลงไฟล์ด้วย:
        # "current_practice": practice_info
    }
    with open('practice_history.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ฟังก์ชันสร้าง ID ใหม่
def generate_practice_id():
    if not practice_history:
        return "001"
    valid_ids = [int(entry["id"]) for entry in practice_history if entry.get("id") and entry["id"].isdigit()]
    if not valid_ids:
        return "001"
    last_id = max(valid_ids)
    return f"{last_id + 1:03d}"

# ฟังก์ชันบันทึกหรืออัปเดตประวัติการซ้อม (สำหรับการซ้อมปัจจุบัน)
def save_current_practice_to_history(): # เปลี่ยนชื่อให้ชัดเจนว่าบันทึก "ปัจจุบัน"
    if all([practice_info.get("id"), practice_info.get("date"), practice_info.get("time"), practice_info.get("location")]):
        # ลบ entry เก่าที่มี ID เดียวกันออกจาก practice_history
        practice_history[:] = [entry for entry in practice_history if entry.get("id") != practice_info["id"]]

        # สร้าง entry ใหม่สำหรับ history
        history_entry = {
            "id": practice_info["id"],
            "date": practice_info["date"],
            "time": practice_info["time"],
            "location": practice_info["location"],
            "members": members.copy(), # ใช้ members ปัจจุบัน
            "is_open_for_signup": practice_info.get("is_open_for_signup", False) # <<<< แก้ไข: เพิ่มสถานะ
        }
        practice_history.append(history_entry)
        practice_history.sort(key=lambda x: x.get("id", "000")) # เรียงตาม ID
        save_history_to_file()

# ฟังก์ชันสร้างข้อความแจ้งเตือนการซ้อมปัจจุบัน
def create_notification():
    if not all([practice_info.get("id"), practice_info.get("date"), practice_info.get("time"), practice_info.get("location")]):
        return None
    notification = f"📢 **การซ้อมครั้งใหม่ (ฉบับที่ {practice_info['id']})**\n"
    notification += f"📅 วันที่: {practice_info['date']}\n"
    notification += f"⏰ เวลา: {practice_info['time']}\n"
    notification += f"📍 สถานที่: {practice_info['location']}\n"
    # --- เพิ่มการแสดงสถานะการลงชื่อ ---
    if practice_info.get("is_open_for_signup", False):
        notification += "สถานะ: ✅ **เปิดรับลงชื่อ**\n"
    else:
        notification += "สถานะ: 🅾️ **ปิดรับลงชื่อแล้ว**\n"
    # --- จบการแสดงสถานะ ---
    notification += "📋 รายชื่อแก๊ง:\n"
    for i, (name, status) in enumerate(members.items(), 1):
        notification += f"{i}. {name} - {status}\n"
    return notification

# ฟังก์ชันสร้างข้อความสรุปตาม ID
def create_summary(practice_id):
    # ตรวจสอบการซ้อมปัจจุบันก่อน
    if practice_info.get("id") == practice_id and all([practice_info.get("date"), practice_info.get("time"), practice_info.get("location")]):
        summary = f"📊 **สรุปการซ้อม (ฉบับที่ {practice_id})**\n"
        summary += f"📅 วันที่: {practice_info['date']}\n"
        summary += f"⏰ เวลา: {practice_info['time']}\n"
        summary += f"📍 สถานที่: {practice_info['location']}\n"
        summary += "📋 รายชื่อแก๊ง:\n"
        # ใช้ members จาก practice_info โดยตรงสำหรับการซ้อมปัจจุบัน
        current_members_for_summary = members
        for i, (name, status) in enumerate(current_members_for_summary.items(), 1):
            summary += f"{i}. {name} - {status}\n"
        return summary

    # ตรวจสอบในประวัติ
    for entry in practice_history:
        if entry.get("id") == practice_id:
            summary = f"📊 **สรุปการซ้อม (ฉบับที่ {practice_id})**\n"
            summary += f"📅 วันที่: {entry['date']}\n"
            summary += f"⏰ เวลา: {entry['time']}\n"
            summary += f"📍 สถานที่: {entry['location']}\n"
            summary += "📋 รายชื่อแก๊ง:\n"
            # ใช้ members จาก entry ใน history
            for i, (name, status) in enumerate(entry['members'].items(), 1):
                summary += f"{i}. {name} - {status}\n"
            return summary
    return f"ไม่พบข้อมูลการซ้อมสำหรับฉบับที่ {practice_id}!"


# ฟังก์ชันอัปเดตสถานะทุก 5 นาที
@tasks.loop(minutes=5)
async def update_status_task():
    if update_enabled:
        global last_practice_message
        announcement_channel = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
        if announcement_channel and practice_info.get("id"): # ตรวจสอบว่ามีการซ้อมปัจจุบัน
            if last_practice_message:
                try: await last_practice_message.delete()
                except discord.errors.NotFound: pass
                except discord.errors.Forbidden: print(f"Bot cannot delete messages in {announcement_channel.name}")
                except Exception as e: print(f"Error deleting message: {e}")

            notification = create_notification()
            if notification:
                try: last_practice_message = await announcement_channel.send(notification)
                except discord.errors.Forbidden: print(f"Bot cannot send messages in {announcement_channel.name}")
                except Exception as e: print(f"Error sending message: {e}")

@bot.event
async def on_ready():
    print(f'Bot {bot.user.name} is online!') # เปลี่ยนเป็น bot.user.name
    load_history_from_file()
    if not update_status_task.is_running():
        update_status_task.start()
    start_server()
    try:
        game_name = f"จัดการซ้อม | {bot.command_prefix}setplay"
        await bot.change_presence(activity=discord.Game(name=game_name))
        print(f"Bot presence set to: Playing {game_name}")
    except Exception as e:
        print(f"Error setting bot presence: {e}")

def in_channel(channel_name_or_id):
    async def predicate(ctx):
        is_correct_channel = False
        if isinstance(channel_name_or_id, int):
            if ctx.channel.id == channel_name_or_id: is_correct_channel = True
        elif isinstance(channel_name_or_id, str):
            if ctx.channel.name.lower() == channel_name_or_id.lower(): is_correct_channel = True

        if not is_correct_channel:
            if isinstance(channel_name_or_id, str):
                await ctx.send(f"ใช้คำสั่งนี้ได้เฉพาะในห้อง '{channel_name_or_id}' เท่านั้น!", ephemeral=True, delete_after=10)
            else:
                await ctx.send(f"ใช้คำสั่งนี้ได้เฉพาะในห้องที่กำหนดเท่านั้น!", ephemeral=True, delete_after=10)
            return False
        return True
    return commands.check(predicate)

@bot.command()
@in_channel(SETTING_CHANNEL_NAME)
async def disable_update(ctx):
    global update_enabled
    if not update_enabled: await ctx.send("การอัปเดตสถานะทุก 5 นาทีถูกปิดอยู่แล้ว!"); return
    update_enabled = False
    save_history_to_file() # บันทึกการตั้งค่า update_enabled
    await ctx.send("ปิดการอัปเดตสถานะทุก 5 นาทีเรียบร้อย!")

@bot.command()
@in_channel(SETTING_CHANNEL_NAME)
async def enable_update(ctx):
    global update_enabled
    if update_enabled: await ctx.send("การอัปเดตสถานะทุก 5 นาทีถูกเปิดอยู่แล้ว!"); return
    update_enabled = True
    save_history_to_file() # บันทึกการตั้งค่า update_enabled
    # อัปเดตทันทีเมื่อเปิด (ถ้ามีการซ้อมปัจจุบัน)
    if practice_info.get("id"):
        global last_practice_message
        announcement_channel = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
        if announcement_channel:
            if last_practice_message:
                try: await last_practice_message.delete()
                except: pass
            notification = create_notification()
            if notification:
                try: last_practice_message = await announcement_channel.send(notification)
                except: pass
    await ctx.send("เปิดการอัปเดตสถานะทุก 5 นาทีเรียบร้อย!")

@bot.command(name="ลงชื่อซ้อม", aliases=["ซ้อมทีม"]) # เพิ่ม alias
@in_channel(SIGNUP_CHANNEL_NAME)
async def sign_up_practice(ctx): # เปลี่ยนชื่อฟังก์ชันให้เป็นสากล
    # <<<< แก้ไข: เพิ่มการตรวจสอบสถานะการเปิดรับลงชื่อ >>>>
    if not practice_info.get("id"):
        await ctx.send("ยังไม่มีการตั้งค่าการซ้อม (ยังไม่เปิดให้ลงชื่อ)!", ephemeral=True, delete_after=10)
        return
    if not practice_info.get("is_open_for_signup", False):
        await ctx.send(f"การซ้อมครั้งนี้ (ฉบับที่ {practice_info['id']}) ปิดรับการลงชื่อแล้ว (อาจมีการสรุปผลไปแล้ว)!", ephemeral=True, delete_after=10)
        return
    # <<<< สิ้นสุดการตรวจสอบ >>>>

    discord_name = ctx.author.name
    member_key_to_update = name_mapping.get(discord_name) # ใช้ .get() ปลอดภัยกว่า

    if member_key_to_update and member_key_to_update in members:
        if members[member_key_to_update] == "มาแล้ว":
            await ctx.send(f"{member_key_to_update} ลงชื่อไปแล้วนี่นาาา!", ephemeral=True, delete_after=10)
            return

        members[member_key_to_update] = "มาแล้ว"
        await ctx.send(f"{member_key_to_update} ลงชื่อซ้อมเรียบร้อยแล้ว!")
        save_current_practice_to_history() # อัปเดตข้อมูลการซ้อมปัจจุบันใน history

        # อัปเดตข้อความแจ้งเตือนทันที
        global last_practice_message
        announcement_channel = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
        if announcement_channel and practice_info.get("id"):
            if last_practice_message:
                try: await last_practice_message.delete()
                except: pass
            notification = create_notification()
            if notification:
                try: last_practice_message = await announcement_channel.send(notification)
                except: pass
    else:
        await ctx.send(f"คุณ ({discord_name}) ไม่ได้อยู่ในรายชื่อที่กำหนด หรือมีการตั้งค่า `name_mapping` ไม่ถูกต้อง", ephemeral=True, delete_after=10)

@bot.command()
async def เช็คสถานะ(ctx):
    if not practice_info.get("id"):
        await ctx.send("ยังไม่มีการตั้งค่าการซ้อมปัจจุบัน!")
        return
    notification = create_notification()
    if notification: await ctx.send(notification)
    else: await ctx.send("เกิดข้อผิดพลาดในการสร้างข้อความแจ้งเตือน!")

@bot.command()
@in_channel(SETTING_CHANNEL_NAME)
async def setplay(ctx):
    # บันทึกข้อมูลการซ้อม "ปัจจุบัน" (ถ้ามี) ลง "ประวัติ" ก่อนเริ่มการซ้อมใหม่
    if practice_info.get("id"):
        # ก่อนบันทึก, อาจจะตั้ง is_open_for_signup ของอันเก่าเป็น False ถ้ายังไม่ได้สรุป
        if practice_info.get("is_open_for_signup", False):
            print(f"Practice ID {practice_info['id']} was still open for signup before new setplay. Closing it.")
            practice_info["is_open_for_signup"] = False
        save_current_practice_to_history()


    def check(m): return m.author == ctx.author and m.channel == ctx.channel

    await ctx.send("กรุณาใส่ข้อมูลการซ้อม:\n1. วันที่ (เช่น 2024-08-15)\n2. เวลา (เช่น 20:00)\n3. สถานที่ (เช่น เซิฟรอง 1)\nพิมพ์แต่ละรายการแล้วกด Enter")
    prompts = ["วันที่ (YYYY-MM-DD):", "เวลา (HH:MM):", "สถานที่:"]
    responses = []
    for i, prompt_text in enumerate(prompts):
        await ctx.send(prompt_text)
        try:
            msg = await bot.wait_for('message', check=check, timeout=120.0)
            content = msg.content.strip()
            if i == 0:
                try: datetime.strptime(content, '%Y-%m-%d')
                except ValueError: await ctx.send("รูปแบบวันที่ไม่ถูกต้อง! (YYYY-MM-DD). เริ่ม !setplay ใหม่"); return
            if i == 1:
                try: datetime.strptime(content, '%H:%M')
                except ValueError: await ctx.send("รูปแบบเวลาไม่ถูกต้อง! (HH:MM). เริ่ม !setplay ใหม่"); return
            responses.append(content)
        except asyncio.TimeoutError: await ctx.send("หมดเวลาป้อนข้อมูล! เริ่ม !setplay ใหม่"); return

    # อัปเดต practice_info สำหรับการซ้อมใหม่
    practice_info["id"] = generate_practice_id()
    practice_info["date"] = responses[0]
    practice_info["time"] = responses[1]
    practice_info["location"] = responses[2]
    practice_info["is_open_for_signup"] = True # <<<< แก้ไข: เปิดให้ลงชื่อสำหรับการซ้อมใหม่

    # รีเซ็ตสถานะสมาชิกสำหรับ members ปัจจุบัน
    for name in members: members[name] = "ขาด"

    save_current_practice_to_history() # บันทึก "การซ้อมปัจจุบัน" ใหม่นี้ลง "ประวัติ" ทันที

    global last_practice_message
    announcement_channel = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
    if announcement_channel:
        if last_practice_message:
            try: await last_practice_message.delete()
            except: pass
        notification = create_notification()
        if notification:
            try:
                last_practice_message = await announcement_channel.send(notification)
                await ctx.send(f"การตั้งค่าการซ้อม (ฉบับที่ {practice_info['id']}) เสร็จสิ้น! ส่งไปห้องประกาศแล้ว")
            except discord.errors.Forbidden:
                await ctx.send(f"ตั้งค่าซ้อม (ฉบับที่ {practice_info['id']}) แล้ว แต่ส่งไปห้องประกาศไม่ได้ (ไม่มีสิทธิ์)")
        else: await ctx.send("ตั้งค่าซ้อมแล้ว แต่สร้างข้อความแจ้งเตือนไม่ได้")
    else: await ctx.send("ไม่พบห้องประกาศ! แต่ตั้งค่าซ้อมแล้ว")

@bot.command()
@in_channel(SETTING_CHANNEL_NAME)
async def สรุป(ctx, practice_id: str):
    if not practice_id.isdigit() or len(practice_id) != 3:
        await ctx.send("กรุณาระบุ ID เป็นตัวเลข 3 หลัก (เช่น 001)"); return

    announcement_channel = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
    if not announcement_channel:
        await ctx.send(f"ไม่พบห้องประกาศ (ID: {ANNOUNCEMENT_CHANNEL_ID})!"); return

    # <<<< แก้ไข: ตรวจสอบและปิดการลงชื่อถ้าเป็น ID ปัจจุบัน >>>>
    if practice_info.get("id") == practice_id:
        if practice_info.get("is_open_for_signup", False): # ถ้ายังเปิดอยู่
            practice_info["is_open_for_signup"] = False
            save_current_practice_to_history() # บันทึกการเปลี่ยนแปลงนี้
            await ctx.send(f"การซ้อมฉบับที่ {practice_id} (ปัจจุบัน) ได้ปิดรับการลงชื่อแล้วเนื่องจากมีการสรุปผล")
        else:
            await ctx.send(f"การซ้อมฉบับที่ {practice_id} (ปัจจุบัน) ปิดรับการลงชื่อไปแล้วก่อนหน้านี้")
    # <<<< สิ้นสุดการแก้ไข >>>>

    summary = create_summary(practice_id)
    try:
        await announcement_channel.send(summary)
        await ctx.send(f"สรุปการซ้อม (ฉบับที่ {practice_id}) ถูกส่งไปยังห้องประกาศแล้ว!")
    except discord.errors.Forbidden:
        await ctx.send(f"สร้างสรุป (ฉบับที่ {practice_id}) ได้ แต่ส่งไปห้องประกาศไม่ได้ (ไม่มีสิทธิ์)")
    except Exception as e:
        await ctx.send(f"เกิดข้อผิดพลาดในการส่งสรุป: {e}")


DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
if DISCORD_TOKEN is None:
    print("Error: DISCORD_TOKEN not found. Please set it in .env or environment variables.")
else:
    try: bot.run(DISCORD_TOKEN)
    except discord.errors.LoginFailure: print("Login Failed: Incorrect token or bot has invalid intents.")
    except Exception as e: print(f"An error occurred: {e}")