# main.py (รวมโค้ดและปรับปรุง)

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
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=8080)

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
    "candy": "ขาด",
    "sindrea": "ขาด",
    "yam": "ขาด",
    "chababa": "ขาด",
    "naila": "ขาด",
}

# ผูกชื่อ Discord กับชื่อในรายการ
name_mapping = {
    "onitsuka3819": "Juno",
    "candy_dayy": "candy",
    "sindrea_cz": "sindrea",
    "yam2196": "yam",
    "chababa.": "chababa",
    "naila_888": "naila",
}

# ตัวแปรเก็บข้อมูลการซ้อมปัจจุบัน
practice_info = {
    "id": None,
    "date": None,
    "time": None,
    "location": None
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
    global practice_history, update_enabled
    try:
        with open('practice_history.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            practice_history = data.get("history", [])
            update_enabled = data.get("update_enabled", True)
        for i, entry in enumerate(practice_history):
            if "id" not in entry or not entry["id"]: # ตรวจสอบ id ที่อาจเป็น null หรือ empty
                # สร้าง id ใหม่หากไม่มี หรือไม่ถูกต้อง (อาจต้องปรับ logic การสร้าง id)
                # สำหรับตอนนี้, เราจะให้ id เป็นเลขลำดับถ้าไม่มี แต่ควรมีระบบ id ที่ดีกว่านี้
                entry["id"] = f"{len(practice_history) - i:03d}" # ตัวอย่างการกำหนด id แบบง่ายๆ
        save_history_to_file() # บันทึกถ้ามีการเปลี่ยนแปลง id
    except FileNotFoundError:
        practice_history = []
        update_enabled = True
    except json.JSONDecodeError:
        print("Error decoding practice_history.json. File might be corrupted or empty.")
        practice_history = []
        update_enabled = True


# ฟังก์ชันบันทึกประวัติและการตั้งค่าลงไฟล์
def save_history_to_file():
    data = {
        "history": practice_history,
        "update_enabled": update_enabled
    }
    with open('practice_history.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ฟังก์ชันสร้าง ID ใหม่
def generate_practice_id():
    if not practice_history:
        return "001"
    # กรอง entry ที่มี id เป็นตัวเลขและไม่เป็น None/empty string
    valid_ids = [int(entry["id"]) for entry in practice_history if entry.get("id") and entry["id"].isdigit()]
    if not valid_ids:
        return "001" # ถ้าไม่มี id ที่เป็นตัวเลขเลย
    last_id = max(valid_ids)
    return f"{last_id + 1:03d}"

# ฟังก์ชันบันทึกหรืออัปเดตประวัติการซ้อม
def save_practice_to_history():
    if all([practice_info["id"], practice_info["date"], practice_info["time"], practice_info["location"]]):
        practice_history[:] = [entry for entry in practice_history if entry.get("id") != practice_info["id"]]
        history_entry = {
            "id": practice_info["id"],
            "date": practice_info["date"],
            "time": practice_info["time"],
            "location": practice_info["location"],
            "members": members.copy()
        }
        practice_history.append(history_entry)
        # เรียงตาม ID ก่อนบันทึก (ถ้าต้องการ)
        practice_history.sort(key=lambda x: x.get("id", "000"))
        save_history_to_file()

# ฟังก์ชันสร้างข้อความแจ้งเตือนการซ้อมปัจจุบัน
def create_notification():
    if not all([practice_info["id"], practice_info["date"], practice_info["time"], practice_info["location"]]):
        return None
    notification = f"📢 **การซ้อมครั้งใหม่ (ฉบับที่ {practice_info['id']})**\n"
    notification += f"📅 วันที่: {practice_info['date']}\n"
    notification += f"⏰ เวลา: {practice_info['time']}\n"
    notification += f"📍 สถานที่: {practice_info['location']}\n"
    notification += "📋 รายชื่อแก๊ง:\n"
    for i, (name, status) in enumerate(members.items(), 1):
        notification += f"{i}. {name} - {status}\n"
    return notification

# ฟังก์ชันสร้างข้อความสรุปตาม ID
def create_summary(practice_id):
    if practice_info.get("id") == practice_id and all([practice_info.get("date"), practice_info.get("time"), practice_info.get("location")]):
        summary = f"📊 **สรุปการซ้อม (ฉบับที่ {practice_id})**\n"
        summary += f"📅 วันที่: {practice_info['date']}\n"
        summary += f"⏰ เวลา: {practice_info['time']}\n"
        summary += f"📍 สถานที่: {practice_info['location']}\n"
        summary += "📋 รายชื่อแก๊ง:\n"
        for i, (name, status) in enumerate(members.items(), 1):
            summary += f"{i}. {name} - {status}\n"
        return summary
    for entry in practice_history:
        if entry.get("id") == practice_id:
            summary = f"📊 **สรุปการซ้อม (ฉบับที่ {practice_id})**\n"
            summary += f"📅 วันที่: {entry['date']}\n"
            summary += f"⏰ เวลา: {entry['time']}\n"
            summary += f"📍 สถานที่: {entry['location']}\n"
            summary += "📋 รายชื่อแก๊ง:\n"
            for i, (name, status) in enumerate(entry['members'].items(), 1):
                summary += f"{i}. {name} - {status}\n"
            return summary
    return f"ไม่พบข้อมูลการซ้อมสำหรับฉบับที่ {practice_id}!"

# ฟังก์ชันอัปเดตสถานะทุก 5 นาที
@tasks.loop(minutes=5)
async def update_status_task(): # เปลี่ยนชื่อฟังก์ชันเล็กน้อยเพื่อไม่ให้ซ้ำกับ event
    if update_enabled:
        global last_practice_message
        announcement_channel = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
        if announcement_channel and practice_info.get("id"):
            if last_practice_message:
                try:
                    await last_practice_message.delete()
                except discord.errors.NotFound:
                    pass # ไม่ต้องทำอะไรถ้าข้อความถูกลบไปแล้ว
                except discord.errors.Forbidden:
                    print(f"Bot does not have permission to delete messages in {announcement_channel.name}")
                except Exception as e:
                    print(f"Error deleting message: {e}")


            notification = create_notification()
            if notification:
                try:
                    last_practice_message = await announcement_channel.send(notification)
                except discord.errors.Forbidden:
                    print(f"Bot does not have permission to send messages in {announcement_channel.name}")
                except Exception as e:
                    print(f"Error sending message: {e}")


@bot.event
async def on_ready():
    print(f'Bot {bot.user} is online!')
    load_history_from_file()
    if not update_status_task.is_running():
        update_status_task.start()
    start_server() # เริ่ม Flask server เมื่อบอทพร้อม

# Decorator สำหรับตรวจสอบห้อง
def in_channel(channel_name_or_id):
    async def predicate(ctx):
        if isinstance(channel_name_or_id, int): # ถ้าเป็น ID
            if ctx.channel.id != channel_name_or_id:
                await ctx.send(f"ใช้คำสั่งนี้ได้เฉพาะในห้องที่กำหนดเท่านั้น!")
                return False
        elif isinstance(channel_name_or_id, str): # ถ้าเป็นชื่อ
            if ctx.channel.name.lower() != channel_name_or_id.lower():
                await ctx.send(f"ใช้คำสั่งนี้ได้เฉพาะในห้อง '{channel_name_or_id}' เท่านั้น!")
                return False
        return True
    return commands.check(predicate)

@bot.command()
@in_channel(SETTING_CHANNEL_NAME)
async def disable_update(ctx):
    global update_enabled
    if not update_enabled:
        await ctx.send("การอัปเดตสถานะทุก 5 นาทีถูกปิดอยู่แล้ว!")
        return
    update_enabled = False
    save_history_to_file()
    await ctx.send("ปิดการอัปเดตสถานะทุก 5 นาทีเรียบร้อย!")

@bot.command()
@in_channel(SETTING_CHANNEL_NAME)
async def enable_update(ctx):
    global update_enabled
    if update_enabled:
        await ctx.send("การอัปเดตสถานะทุก 5 นาทีถูกเปิดอยู่แล้ว!")
        return
    update_enabled = True
    save_history_to_file()
    announcement_channel = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
    if announcement_channel and practice_info.get("id"):
        global last_practice_message
        if last_practice_message:
            try:
                await last_practice_message.delete()
            except discord.errors.NotFound: pass
            except discord.errors.Forbidden: print("Cannot delete last_practice_message: Forbidden")
        notification = create_notification()
        if notification:
            try:
                last_practice_message = await announcement_channel.send(notification)
            except discord.errors.Forbidden: print("Cannot send notification: Forbidden")
    await ctx.send("เปิดการอัปเดตสถานะทุก 5 นาทีเรียบร้อย!")

@bot.command()
@in_channel(SIGNUP_CHANNEL_NAME)
async def ลงชื่อซ้อม(ctx):
    discord_name = ctx.author.name # หรือ ctx.author.display_name ถ้าต้องการชื่อเล่นในเซิร์ฟเวอร์
    member_key_to_update = None

    # หา key ใน name_mapping จาก discord_name
    for key, value in name_mapping.items():
        # สามารถปรับปรุงการ match ตรงนี้ได้ อาจจะใช้ ctx.author.id ถ้า discord_name ไม่ unique
        if key.lower() == discord_name.lower():
            member_key_to_update = value
            break
    
    if member_key_to_update and member_key_to_update in members:
        members[member_key_to_update] = "มาแล้ว"
        await ctx.send(f"{member_key_to_update} ลงชื่อซ้อมเรียบร้อยแล้ว!")
        save_practice_to_history()

        global last_practice_message
        announcement_channel = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
        if announcement_channel and practice_info.get("id"):
            if last_practice_message:
                try:
                    await last_practice_message.delete()
                except discord.errors.NotFound: pass
                except discord.errors.Forbidden: print("Cannot delete last_practice_message: Forbidden")

            notification = create_notification()
            if notification:
                try:
                    last_practice_message = await announcement_channel.send(notification)
                except discord.errors.Forbidden: print("Cannot send notification: Forbidden")
    else:
        await ctx.send(f"คุณ ({discord_name}) ไม่ได้อยู่ในรายชื่อที่กำหนด หรือมีการตั้งค่า `name_mapping` ไม่ถูกต้อง")


@bot.command()
async def เช็คสถานะ(ctx): # อาจจะจำกัดห้องด้วยก็ได้
    if not practice_info.get("id"):
        await ctx.send("ยังไม่มีการตั้งค่าการซ้อม!")
        return
    notification = create_notification()
    if notification:
        await ctx.send(notification)
    else:
        await ctx.send("เกิดข้อผิดพลาดในการสร้างข้อความแจ้งเตือน (อาจยังไม่ได้ตั้งค่าการซ้อม)!")

@bot.command()
@in_channel(SETTING_CHANNEL_NAME)
async def setplay(ctx):
    # บันทึกข้อมูลการซ้อมเก่าก่อนรีเซ็ต (ถ้ามี id)
    if practice_info.get("id"):
        save_practice_to_history()

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    await ctx.send("กรุณาใส่ข้อมูลการซ้อม:\n1. วันที่ (เช่น 2024-08-15)\n2. เวลา (เช่น 20:00)\n3. สถานที่ (เช่น เซิฟรอง 1)\nพิมพ์แต่ละรายการแล้วกด Enter รอรับข้อความยืนยันทีละขั้น")

    prompts = ["วันที่ (YYYY-MM-DD):", "เวลา (HH:MM):", "สถานที่:"]
    responses = []

    for i, prompt_text in enumerate(prompts):
        await ctx.send(prompt_text)
        try:
            msg = await bot.wait_for('message', check=check, timeout=120.0)
            content = msg.content.strip()
            if i == 0: # ตรวจสอบรูปแบบวันที่
                try:
                    datetime.strptime(content, '%Y-%m-%d')
                except ValueError:
                    await ctx.send("รูปแบบวันที่ไม่ถูกต้อง! ใช้ YYYY-MM-DD (เช่น 2024-08-15). กรุณาเริ่ม !setplay ใหม่")
                    return
            if i == 1: # ตรวจสอบรูปแบบเวลา (เบื้องต้น)
                try:
                    datetime.strptime(content, '%H:%M')
                except ValueError:
                     await ctx.send("รูปแบบเวลาไม่ถูกต้อง! ใช้ HH:MM (เช่น 20:00). กรุณาเริ่ม !setplay ใหม่")
                     return
            responses.append(content)
        except asyncio.TimeoutError:
            await ctx.send("หมดเวลาการป้อนข้อมูล! กรุณาใช้คำสั่ง !setplay ใหม่")
            return

    practice_info["id"] = generate_practice_id()
    practice_info["date"] = responses[0]
    practice_info["time"] = responses[1]
    practice_info["location"] = responses[2]

    for name in members:
        members[name] = "ขาด"

    save_practice_to_history() # บันทึกข้อมูลใหม่

    global last_practice_message
    announcement_channel = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
    if announcement_channel:
        if last_practice_message:
            try:
                await last_practice_message.delete()
            except discord.errors.NotFound: pass
            except discord.errors.Forbidden: print("Cannot delete last_practice_message: Forbidden")
        notification = create_notification()
        if notification:
            try:
                last_practice_message = await announcement_channel.send(notification)
                await ctx.send(f"การตั้งค่าการซ้อม (ฉบับที่ {practice_info['id']}) เสร็จสิ้น! ข้อมูลได้ถูกส่งไปยังห้องประกาศแล้ว")
            except discord.errors.Forbidden:
                await ctx.send(f"การตั้งค่าการซ้อม (ฉบับที่ {practice_info['id']}) เสร็จสิ้น แต่ไม่สามารถส่งข้อความไปยังห้องประกาศได้ (ไม่มีสิทธิ์)")
        else:
            await ctx.send("ตั้งค่าการซ้อมแล้ว แต่ไม่สามารถสร้างข้อความแจ้งเตือนได้")
    else:
        await ctx.send("ไม่พบห้องประกาศ! แต่การตั้งค่าการซ้อมถูกบันทึกแล้ว")


@bot.command()
@in_channel(SETTING_CHANNEL_NAME)
async def สรุป(ctx, practice_id: str):
    if not practice_id.isdigit() or len(practice_id) != 3:
        await ctx.send("กรุณาระบุ ID เป็นตัวเลข 3 หลัก (เช่น 001)")
        return

    announcement_channel = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
    if not announcement_channel:
        await ctx.send(f"ไม่พบห้องประกาศ (ID: {ANNOUNCEMENT_CHANNEL_ID})!")
        return

    summary = create_summary(practice_id)
    try:
        await announcement_channel.send(summary)
        await ctx.send(f"สรุปการซ้อม (ฉบับที่ {practice_id}) ถูกส่งไปยังห้องประกาศแล้ว!")
    except discord.errors.Forbidden:
        await ctx.send(f"สามารถสร้างสรุปการซ้อม (ฉบับที่ {practice_id}) ได้ แต่ไม่สามารถส่งไปยังห้องประกาศ (ไม่มีสิทธิ์)")
    except Exception as e:
        await ctx.send(f"เกิดข้อผิดพลาดในการส่งสรุป: {e}")


# ดึง Token จาก environment variable ที่ชื่อว่า DISCORD_TOKEN
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

if DISCORD_TOKEN is None:
    print("Error: DISCORD_TOKEN not found in .env file or environment variables.")
    print("Please create a .env file with DISCORD_TOKEN='your_bot_token_here'")
else:
    try:
        bot.run(DISCORD_TOKEN)
    except discord.errors.LoginFailure:
        print("Login Failed: Incorrect token or bot has invalid intents.")
    except Exception as e:
        print(f"An error occurred while running the bot: {e}")
