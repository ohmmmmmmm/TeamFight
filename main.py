# main.py (เวอร์ชันรวมโค้드สมบูรณ์ที่สุดเท่าที่ทำได้)

import discord
from discord.ext import commands, tasks
import asyncio
from datetime import datetime, timedelta # เพิ่ม timedelta ถ้าจะใช้คำนวณเวลาใน help หรือที่อื่น
import pytz
import json
import os
from dotenv import load_dotenv
import traceback # สำหรับ error handling

# --- ส่วนของ Flask Server ---
from flask import Flask
from threading import Thread

flask_instance = Flask('') # เปลี่ยนชื่อตัวแปรไม่ให้ซ้ำกับ module 'app' ที่อาจมีคนใช้

@flask_instance.route('/')
def flask_home_route(): # เปลี่ยนชื่อฟังก์ชัน
    return "Practice Management Bot is alive!"

def run_flask_server(): # เปลี่ยนชื่อฟังก์ชัน
    port = int(os.environ.get('PORT', 8080))
    print(f"[{datetime.now(TZ_BANGKOK).strftime('%Y-%m-%d %H:%M:%S')}] Flask server attempting to run on host 0.0.0.0, port {port}")
    try:
        # ควรใช้ WSGI server ที่เหมาะสมสำหรับ production เช่น gunicorn, waitress
        # แต่สำหรับ Render Free Tier, Flask's built-in server ก็พอใช้ได้
        flask_instance.run(host='0.0.0.0', port=port)
    except Exception as e_flask_run:
        print(f"[{datetime.now(TZ_BANGKOK).strftime('%Y-%m-%d %H:%M:%S')}] !!! ERROR starting Flask server: {e_flask_run}")


def start_keep_alive_server(): # เปลี่ยนชื่อฟังก์ชัน
    t = Thread(target=run_flask_server)
    t.daemon = True
    t.start()
    print(f"[{datetime.now(TZ_BANGKOK).strftime('%Y-%m-%d %H:%M:%S')}] Keep-alive server thread initiated.")

# --- จบส่วนของ Flask Server ---

load_dotenv()

# --- การตั้งค่า Bot ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True # เพิ่ม Guilds intent เผื่อใช้ในอนาคต (เช่น on_guild_join)

# ปิด Default Help Command เพื่อใช้ Custom Help Command
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)
TZ_BANGKOK = pytz.timezone('Asia/Bangkok')

# --- ข้อมูลหลักของระบบ (Global Variables) ---
# ควรพิจารณาใช้ config file หรือ database ในระยะยาว
members = {
    "Juno": "ขาด ⛔",
    "Candy": "ขาด ⛔",
    "Sindrea": "ขาด ⛔",
    "Yam": "ขาด ⛔",
    "Chababa": "ขาด ⛔",
    "Naila": "ขาด ⛔",
    "HeiHei": "ขาด ⛔",
    "HoneyLex": "ขาด ⛔",
    "Aiikz": "ขาด ⛔",
    "Hanna": "ขาด ⛔",
    "Songkran": "ขาด ⛔",
}
name_mapping = {
    "onitsuka3819": "Juno",
    "candy_dayy": "Candy",
    "sindrea_cz": "Sindrea",
    "yam2196": "Yam",
    "chababa.": "Chababa",
    "naila_888": "Naila",
    "ms.k3144": "HeiHei",
    "honeylexfahwabwab": "HoneyLex",
    "aiikz": "Aiikz",
    "hanna05682": "Hanna",
    "songkran_gbn": "Songkran",
}
practice_info = {
    "id": None, "date": None, "time": None, "location": None,
    "is_open_for_signup": False
}
practice_history = []
last_practice_message = None # Discord message object for the current practice
update_enabled = True

# --- ค่าคงที่ ---
HISTORY_FILE_PATH = 'practice_history_data.json' # เปลี่ยนชื่อไฟล์เล็กน้อย
ANNOUNCEMENT_CHANNEL_ID = 1375796432140763216 # **สำคัญมาก: ใส่ ID ห้องประกาศที่ถูกต้อง**
SETTING_CHANNEL_NAME = "🔥┃setting"
SIGNUP_CHANNEL_NAME = "🔥┃ลงชื่อซ้อม"

# --- ฟังก์ชันช่วย Log ---
def log_message(message_text, level="INFO"): # เปลี่ยนชื่อและเพิ่ม level
    timestamp = datetime.now(TZ_BANGKOK).strftime('%Y-%m-%d %H:%M:%S %Z')
    print(f"[{timestamp}] [{level}] {message_text}")

# --- ฟังก์ชันจัดการข้อมูล ---
def load_all_data():
    global practice_history, update_enabled, practice_info
    try:
        with open(HISTORY_FILE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        practice_history = data.get("history", [])
        update_enabled = data.get("update_enabled", True)
        # practice_info ถูกรีเซ็ตเมื่อบอทเริ่ม, จะถูกตั้งค่าโดย !setplay เท่านั้น
        practice_info = {"id": None, "date": None, "time": None, "location": None, "is_open_for_signup": False}

        history_was_modified = False
        for i, entry in enumerate(practice_history):
            if not entry.get("id") or not entry["id"].isdigit() or len(entry["id"]) != 3:
                entry["id"] = f"{len(practice_history) - i:03d}" # สร้าง ID ชั่วคราวถ้าไม่ถูกต้อง
                history_was_modified = True
            if "is_open_for_signup" not in entry:
                entry["is_open_for_signup"] = False # entry เก่าถือว่าปิดรับแล้ว
                history_was_modified = True
        if history_was_modified:
            save_all_data()
        log_message(f"Data loaded. History: {len(practice_history)} entries, Update Task: {'Enabled' if update_enabled else 'Disabled'}")
    except FileNotFoundError:
        log_message(f"'{HISTORY_FILE_PATH}' not found. Initializing with empty data.", level="WARNING")
        practice_history, update_enabled = [], True
        practice_info = {"id": None, "date": None, "time": None, "location": None, "is_open_for_signup": False}
        save_all_data() # สร้างไฟล์ใหม่
    except json.JSONDecodeError:
        log_message(f"Error decoding '{HISTORY_FILE_PATH}'. File might be corrupted. Initializing.", level="ERROR")
        # พิจารณาสร้าง backup ของไฟล์ที่เสียหายก่อนเขียนทับ
        practice_history, update_enabled = [], True
        practice_info = {"id": None, "date": None, "time": None, "location": None, "is_open_for_signup": False}
    except Exception as e:
        log_message(f"Unexpected error during load_all_data: {e}", level="ERROR")
        traceback.print_exc()

def save_all_data():
    data_to_persist = {"history": practice_history, "update_enabled": update_enabled}
    try:
        with open(HISTORY_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(data_to_persist, f, ensure_ascii=False, indent=4)
    except Exception as e:
        log_message(f"ERROR saving data to '{HISTORY_FILE_PATH}': {e}", level="ERROR")

def generate_next_practice_id():
    if not practice_history: return "001"
    numeric_ids = [int(e["id"]) for e in practice_history if e.get("id") and e["id"].isdigit() and len(e["id"]) == 3]
    return f"{(max(numeric_ids) if numeric_ids else 0) + 1:03d}"

def archive_current_practice_details():
    """บันทึกรายละเอียดการซ้อมปัจจุบัน (จาก practice_info) ลงใน practice_history"""
    if practice_info.get("id") and all(practice_info.get(k) for k in ["date", "time", "location"]):
        entry_to_archive = {
            "id": practice_info["id"],
            "date": practice_info["date"],
            "time": practice_info["time"],
            "location": practice_info["location"],
            "members": members.copy(), # สมาชิก ณ เวลานั้น
            "is_open_for_signup": practice_info.get("is_open_for_signup", False)
        }
        # ลบ entry เก่าที่มี ID เดียวกันออกก่อน (ถ้ามี) เพื่ออัปเดต
        practice_history[:] = [entry for entry in practice_history if entry.get("id") != practice_info["id"]]
        practice_history.append(entry_to_archive)
        practice_history.sort(key=lambda x: x.get("id", "000")) # เรียงตาม ID
        save_all_data()
        log_message(f"Archived/Updated practice ID {practice_info['id']} in history.")

# --- ฟังก์ชันสร้าง Embeds ---
def create_current_practice_notification_embed():
    if not all(practice_info.get(k) for k in ["id", "date", "time", "location"]): return None
    embed = discord.Embed(
        title=f"📢 การซ้อม (ฉบับที่ {practice_info['id']})",
        color=discord.Color.green() if practice_info.get("is_open_for_signup") else discord.Color.dark_orange()
    )
    embed.add_field(name="📅 วันที่", value=practice_info['date'], inline=True)
    embed.add_field(name="⏰ เวลา", value=practice_info['time'], inline=True)
    embed.add_field(name="📍 สถานที่", value=f"`{practice_info['location']}`", inline=False)
    status_text = "✅ **เปิดรับลงชื่อ**" if practice_info.get("is_open_for_signup") else "🅾️ **ปิดรับลงชื่อแล้ว**"
    embed.add_field(name="📝 สถานะ", value=status_text, inline=False)
    member_lines = [f"• {name}: `{status}`" for name, status in members.items()]
    embed.add_field(name="👥 สมาชิกทีม", value="\n".join(member_lines) or "ไม่มีข้อมูลสมาชิก", inline=False)
    embed.set_footer(text=f"อัปเดตล่าสุด: {datetime.now(TZ_BANGKOK).strftime('%d %b %Y, %H:%M:%S')}")
    if bot.user and bot.user.display_avatar: embed.set_thumbnail(url=bot.user.display_avatar.url)
    return embed

def create_practice_summary_embed_by_id(id_to_summarize: str):
    source = None
    summary_members_state = None
    if practice_info.get("id") == id_to_summarize:
        source = practice_info
        summary_members_state = members # ใช้สถานะ members ปัจจุบันสำหรับสรุปการซ้อมปัจจุบัน
    else:
        for entry in practice_history:
            if entry.get("id") == id_to_summarize:
                source = entry
                summary_members_state = entry.get("members", {}) # ใช้ members ที่บันทึกไว้ใน history
                break
    if not source or not all(source.get(k) for k in ["date", "time", "location"]):
        return discord.Embed(title="ไม่พบข้อมูลการซ้อม", description=f"ไม่พบข้อมูลสำหรับฉบับที่ `{id_to_summarize}`", color=discord.Color.red())

    embed = discord.Embed(title=f"📊 สรุปผลการซ้อม (ฉบับที่ {id_to_summarize})", color=discord.Color.gold())
    embed.add_field(name="📅 วันที่", value=source['date'], inline=True)
    embed.add_field(name="⏰ เวลา", value=source['time'], inline=True)
    embed.add_field(name="📍 สถานที่", value=f"`{source['location']}`", inline=False)
    member_lines = [f"• {name}: `{status}`" for name, status in summary_members_state.items()]
    embed.add_field(name="👥 ผลการเข้าร่วม", value="\n".join(member_lines) or "ไม่มีข้อมูลการลงชื่อ", inline=False)
    embed.set_footer(text=f"สร้างสรุปเมื่อ: {datetime.now(TZ_BANGKOK).strftime('%d %b %Y, %H:%M:%S')}")
    return embed

# --- Tasks ---
@tasks.loop(minutes=5)
async def auto_update_status_message_task():
    global last_practice_message
    if not update_enabled or not practice_info.get("id") or not bot.is_ready(): return

    announcement_channel = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
    if not announcement_channel:
        log_message(f"Announcement channel ID {ANNOUNCEMENT_CHANNEL_ID} not found for auto-update.", "ERROR")
        return

    if last_practice_message:
        try: await last_practice_message.delete()
        except (discord.NotFound, discord.Forbidden): pass
        except Exception as e: log_message(f"Error deleting old status message for auto-update: {e}", "WARNING")
        finally: last_practice_message = None # Ensure it's reset

    notification_embed = create_current_practice_notification_embed()
    if notification_embed:
        try: last_practice_message = await announcement_channel.send(embed=notification_embed)
        except discord.Forbidden: log_message(f"Bot lacks permission to send messages in announcement channel for auto-update.", "ERROR")
        except Exception as e: log_message(f"Error sending new status message for auto-update: {e}", "ERROR")

# --- Custom Help Command ---
class CustomHelp(commands.HelpCommand):
    def __init__(self):
        super().__init__(command_attrs={
            'help': 'แสดงข้อความช่วยเหลือนี้',
            'aliases': ['ช่วยเหลือ', 'h', 'คำสั่ง', 'cmd']
        })

    async def send_bot_help(self, mapping):
        embed = discord.Embed(
            title="🤖 ศูนย์ช่วยเหลือ Bot จัดการซ้อม",
            description=f"ใช้ prefix `{self.context.prefix}` ตามด้วยชื่อคำสั่ง (เช่น `{self.context.prefix}ลงชื่อซ้อม`)\n"
                        f"พิมพ์ `{self.context.prefix}help <ชื่อคำสั่ง>` เพื่อดูรายละเอียดเพิ่มเติมของคำสั่งนั้นๆ",
            color=discord.Color.from_rgb(173, 216, 230) # Light Blue
        )
        if self.context.bot.user and self.context.bot.user.display_avatar:
            embed.set_thumbnail(url=self.context.bot.user.display_avatar.url)

        for cog, command_list in mapping.items():
            filtered_cmds = await self.filter_commands(command_list, sort=True)
            if not filtered_cmds: continue

            cmd_details = []
            for cmd in filtered_cmds:
                signature = self.get_command_signature(cmd)
                help_text = cmd.help or "ไม่มีคำอธิบาย"
                cmd_details.append(f"**`{signature}`**\n*{help_text}*")
            
            cog_name = cog.qualified_name if cog else "คำสั่งทั่วไป"
            embed.add_field(name=f"**{cog_name}**", value="\n\n".join(cmd_details), inline=False)
        
        destination = self.get_destination()
        await destination.send(embed=embed)
        log_message(f"Help command invoked by {self.context.author} in #{self.context.channel}")

    async def send_command_help(self, command):
        if not await self.filter_commands([command]):
            await self.send_error_message(await self.command_not_found(command.qualified_name))
            return

        embed = discord.Embed(
            title=f"🔍 คำสั่ง: `{self.get_command_signature(command)}`",
            description=command.help or "ไม่มีคำอธิบายสำหรับคำสั่งนี้",
            color=discord.Color.from_rgb(144, 238, 144) # Light Green
        )
        if command.aliases:
            embed.add_field(name="ชื่อเรียกอื่น (Aliases)", value="`, `".join(command.aliases), inline=False)
        
        # Example for adding usage if you define it in command (e.g., command.usage = "<argument1> [optional_argument]")
        # usage = self.get_command_signature(command) # This already includes params
        # embed.add_field(name="วิธีใช้", value=f"`{usage}`", inline=False)
        
        destination = self.get_destination()
        await destination.send(embed=embed)
        log_message(f"Help for command '{command.name}' invoked by {self.context.author}")

    async def send_group_help(self, group): # For command groups, if you use them
        embed = discord.Embed(title=f"กลุ่มคำสั่ง: `{self.get_command_signature(group)}`", description=group.help or "ไม่มีคำอธิบายกลุ่มคำสั่ง", color=discord.Color.dark_gold())
        filtered_cmds = await self.filter_commands(group.commands, sort=True)
        for cmd in filtered_cmds:
            embed.add_field(name=self.get_command_signature(cmd), value=cmd.short_doc or cmd.help or "ไม่มีคำอธิบายย่อ", inline=False)
        destination = self.get_destination()
        await destination.send(embed=embed)

    async def command_not_found(self, string): return f"ไม่พบคำสั่งชื่อ `{string}`"
    async def subcommand_not_found(self, command, string): return f"คำสั่งย่อย `{string}` ไม่พบในกลุ่ม `{command.qualified_name}`"
    async def send_error_message(self, error_text):
        destination = self.get_destination()
        await destination.send(f"😕 {error_text}", delete_after=10)
        log_message(f"Help system error: {error_text}", "WARNING")

bot.help_command = CustomHelp()
# --- จบ Custom Help Command ---


# --- Bot Events ---
@bot.event
async def on_ready():
    log_message(f"Bot {bot.user.name} (ID: {bot.user.id}) is online and ready!")
    load_all_data()
    if not auto_update_status_message_task.is_running():
        auto_update_status_message_task.start()
        log_message("Auto-update status message task started.")
    start_keep_alive_server()
    try:
        activity_name = f"จัดการทีม | {bot.command_prefix}help"
        await bot.change_presence(activity=discord.Game(name=activity_name))
        log_message(f"Bot presence set to: Playing {activity_name}")
    except Exception as e: log_message(f"Error setting bot presence: {e}", "WARNING")

# --- Decorators & Checks ---
def check_if_correct_channel(channel_name_or_id):
    async def predicate(ctx):
        is_valid_channel = False
        if isinstance(channel_name_or_id, int): is_valid_channel = (ctx.channel.id == channel_name_or_id)
        elif isinstance(channel_name_or_id, str): is_valid_channel = (ctx.channel.name.lower() == channel_name_or_id.lower())
        
        if not is_valid_channel:
            err_msg = f"คำสั่งนี้ใช้ได้เฉพาะในห้อง '{channel_name_or_id}'" if isinstance(channel_name_or_id, str) else "คำสั่งนี้ใช้ได้ในห้องที่กำหนดเท่านั้น"
            try: await ctx.send(f"🚫 {err_msg}", ephemeral=True, delete_after=10)
            except: pass # Ignore if can't send ephemeral
        return is_valid_channel
    return commands.check(predicate)

# --- Bot Commands ---
@bot.command(name="ปิดอัปเดต", aliases=["disableupdate"], help="ปิดการส่งข้อความสถานะการซ้อมไปห้องประกาศทุก 5 นาที (Admin เท่านั้น)")
@check_if_correct_channel(SETTING_CHANNEL_NAME)
@commands.has_permissions(administrator=True)
async def cmd_disable_update(ctx):
    global update_enabled
    if not update_enabled: await ctx.send("การอัปเดตปิดอยู่แล้ว", ephemeral=True, delete_after=7); return
    update_enabled = False; save_all_data()
    await ctx.send("✅ ปิดการอัปเดตสถานะอัตโนมัติแล้ว", ephemeral=True)

@bot.command(name="เปิดอัปเดต", aliases=["enableupdate"], help="เปิดการส่งข้อความสถานะการซ้อมไปห้องประกาศทุก 5 นาที (Admin เท่านั้น)")
@check_if_correct_channel(SETTING_CHANNEL_NAME)
@commands.has_permissions(administrator=True)
async def cmd_enable_update(ctx):
    global update_enabled, last_practice_message
    if update_enabled: await ctx.send("การอัปเดตเปิดอยู่แล้ว", ephemeral=True, delete_after=7); return
    update_enabled = True; save_all_data()
    await ctx.send("✅ เปิดการอัปเดตสถานะอัตโนมัติแล้ว", ephemeral=True)
    if practice_info.get("id"): # ลองอัปเดตทันที
        ann_ch = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
        if ann_ch:
            if last_practice_message:
                try: await last_practice_message.delete(); last_practice_message = None
                except: pass
            embed = create_current_practice_notification_embed()
            if embed:
                try: last_practice_message = await ann_ch.send(embed=embed)
                except: pass

@bot.command(name="ลงชื่อซ้อม", aliases=["ซ้อมทีม"], help=f"ลงชื่อเข้าร่วมการซ้อมปัจจุบัน (ใช้ในห้อง '{SIGNUP_CHANNEL_NAME}')")
@check_if_correct_channel(SIGNUP_CHANNEL_NAME)
async def cmd_signup_practice(ctx):
    user_command_msg = ctx.message # เก็บข้อความคำสั่งไว้ลบทีหลัง
    
    async def delete_user_command(): # ฟังก์ชันช่วยลบข้อความ
        try: await user_command_msg.delete()
        except discord.Forbidden: log_message(f"Bot lacks 'Manage Messages' in #{ctx.channel.name}", "WARNING")
        except discord.HTTPException: pass # อาจจะถูกลบไปแล้ว

    if not practice_info.get("id"):
        await ctx.send("⚠️ ยังไม่มีการตั้งค่าการซ้อมปัจจุบัน", ephemeral=True, delete_after=10)
        await delete_user_command()
        return
        
    if not practice_info.get("is_open_for_signup", False):
        await ctx.send(f"🅾️ การซ้อม (ฉบับที่ {practice_info['id']}) ปิดรับการลงชื่อแล้ว", ephemeral=True, delete_after=10)
        await delete_user_command()
        return

    discord_account_name = ctx.author.name # หรือ ctx.author.display_name สำหรับชื่อเล่นในเซิร์ฟเวอร์
    team_member_name = name_mapping.get(discord_account_name)

    if team_member_name and team_member_name in members:
        if members[team_member_name] == "มาแล้ว ✅":
            await ctx.send(f"👍 {team_member_name} ได้ลงชื่อเข้าร่วมไปแล้ว", ephemeral=True, delete_after=7)
        else:
            members[team_member_name] = "มาแล้ว ✅"
            await ctx.send(f"✅ {team_member_name} ลงชื่อซ้อมเรียบร้อย!", delete_after=7) # แจ้งผู้ใช้
            archive_current_practice_details() # อัปเดตข้อมูลการซ้อมปัจจุบันใน history

            if update_enabled: # อัปเดตข้อความในห้องประกาศทันที
                global last_practice_message
                ann_ch = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
                if ann_ch:
                    if last_practice_message:
                        try: await last_practice_message.delete(); last_practice_message = None
                        except: pass
                    embed = create_current_practice_notification_embed()
                    if embed:
                        try: last_practice_message = await ann_ch.send(embed=embed)
                        except: pass
    else:
        await ctx.send(f"❓ ไม่พบชื่อบัญชี Discord ของคุณ ({discord_account_name}) ในระบบลงทะเบียนของทีม", ephemeral=True, delete_after=10)
    
    await delete_user_command() # ลบข้อความคำสั่งของผู้ใช้

@bot.command(name="เช็คสถานะ", aliases=["สถานะซ้อม"], help="แสดงข้อมูลและสถานะการลงชื่อของการซ้อมปัจจุบัน")
async def cmd_check_status(ctx):
    if not practice_info.get("id"):
        await ctx.send("ยังไม่มีการตั้งค่าการซ้อมปัจจุบัน", ephemeral=True, delete_after=10); return
    embed = create_current_practice_notification_embed()
    if embed: await ctx.send(embed=embed)
    else: await ctx.send("เกิดข้อผิดพลาดในการสร้างข้อความสถานะ", ephemeral=True, delete_after=10)

@bot.command(name="ตั้งค่าซ้อม", aliases=["setplay"], help="เริ่มการซ้อมใหม่: กำหนดวัน, เวลา, และสถานที่ (Admin, ในห้อง Setting)")
@check_if_correct_channel(SETTING_CHANNEL_NAME)
@commands.has_permissions(manage_guild=True) # หรือ role ที่เฉพาะเจาะจงกว่า
async def cmd_set_practice(ctx):
    if practice_info.get("id"): # ถ้ามีการซ้อมเก่าค้างอยู่
        if practice_info.get("is_open_for_signup"): practice_info["is_open_for_signup"] = False # ปิดอันเก่า
        archive_current_practice_details() # บันทึกอันเก่าก่อน

    def check_author_channel(m): return m.author == ctx.author and m.channel == ctx.channel
    
    practice_details_prompts = [
        ("วันที่ซ้อม (YYYY-MM-DD):", '%Y-%m-%d', "date", "2024-12-31"),
        ("เวลาซ้อม (HH:MM 24hr):", '%H:%M', "time", "20:00"),
        ("สถานที่ซ้อม:", None, "location", "Discord Voice / In-Game Server")
    ]
    collected_data = {}
    await ctx.send(f"📝 **เริ่มต้นตั้งค่าการซ้อมใหม่** (ตอบทีละรายการ, พิมพ์ `ยกเลิก` เพื่อหยุด):")

    for prompt_text, date_format, data_key, example_text in practice_details_prompts:
        await ctx.send(f"{prompt_text} (ตัวอย่าง: `{example_text}`)")
        try:
            msg = await bot.wait_for('message', check=check_author_channel, timeout=180.0)
            content = msg.content.strip()
            if content.lower() == 'ยกเลิก':
                await ctx.send("🚫 ยกเลิกการตั้งค่าซ้อมแล้ว", ephemeral=True); return
            if date_format: datetime.strptime(content, date_format) # ตรวจสอบ format
            if not content: # ป้องกันค่าว่าง
                await ctx.send(f"⚠️ ข้อมูลสำหรับ '{data_key}' ไม่ควรเป็นค่าว่าง กรุณาเริ่มใหม่", ephemeral=True); return
            collected_data[data_key] = content
        except ValueError:
            await ctx.send(f"⚠️ รูปแบบข้อมูลสำหรับ '{data_key}' ไม่ถูกต้อง (ตัวอย่าง: `{example_text}`). กรุณาเริ่มใหม่", ephemeral=True); return
        except asyncio.TimeoutError:
            await ctx.send("⏰ หมดเวลาการป้อนข้อมูล กรุณาเริ่มใหม่", ephemeral=True); return

    practice_info["id"] = generate_next_practice_id()
    practice_info.update(collected_data)
    practice_info["is_open_for_signup"] = True
    for member_name in members: members[member_name] = "ขาด ⛔" # รีเซ็ตสถานะสมาชิก
    archive_current_practice_details() # บันทึกการซ้อมใหม่นี้
    
    await ctx.send(f"✅ **ตั้งค่าการซ้อมใหม่ (ฉบับที่ {practice_info['id']}) เรียบร้อยแล้ว!**\n"
                   f"วันที่: {practice_info['date']}, เวลา: {practice_info['time']}, สถานที่: {practice_info['location']}",
                   ephemeral=True)

    global last_practice_message # อัปเดตห้องประกาศ
    ann_ch = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
    if ann_ch:
        if last_practice_message:
            try: await last_practice_message.delete(); last_practice_message = None
            except: pass
        embed = create_current_practice_notification_embed()
        if embed:
            try: last_practice_message = await ann_ch.send(embed=embed)
            except discord.Forbidden: log_message(f"Bot lacks permission to send new practice to announcement channel.", "ERROR")
    else: log_message(f"Announcement channel ID {ANNOUNCEMENT_CHANNEL_ID} not found for new practice.", "ERROR")

@bot.command(name="สรุปผล", aliases=["สรุป"], help="ส่งสรุปผลการซ้อมตาม ID ที่ระบุไปยังห้องประกาศ (Admin, ในห้อง Setting)")
@check_if_correct_channel(SETTING_CHANNEL_NAME)
@commands.has_permissions(manage_guild=True)
async def cmd_summarize_practice(ctx, practice_id: str):
    if not (practice_id.isdigit() and len(practice_id) == 3):
        await ctx.send("⚠️ ID การซ้อมต้องเป็นตัวเลข 3 หลัก (เช่น `001`)", ephemeral=True, delete_after=10); return

    feedback = []
    if practice_info.get("id") == practice_id and practice_info.get("is_open_for_signup"):
        practice_info["is_open_for_signup"] = False
        archive_current_practice_details()
        feedback.append(f"การซ้อมปัจจุบัน (ฉบับที่ {practice_id}) ได้ปิดรับการลงชื่อเนื่องจากการสรุปผล")
    
    announcement_ch = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
    if not announcement_ch:
        await ctx.send(f"❌ ไม่พบห้องประกาศ (ID: {ANNOUNCEMENT_CHANNEL_ID})", ephemeral=True); return

    summary_embed = create_practice_summary_embed_by_id(practice_id)
    if "ไม่พบข้อมูล" in summary_embed.title: # ตรวจสอบจาก Embed ที่สร้าง
        await ctx.send(summary_embed.description, ephemeral=True, delete_after=10); return

    try:
        await announcement_ch.send(embed=summary_embed)
        feedback.append(f"📊 สรุปการซ้อม (ฉบับที่ {practice_id}) ถูกส่งไปห้องประกาศแล้ว!")
    except discord.Forbidden:
        feedback.append(f"⚠️ สร้างสรุป (ฉบับที่ {practice_id}) ได้ แต่บอทไม่มีสิทธิ์ส่งไปห้องประกาศ")
    except Exception as e:
        feedback.append(f"❌ เกิดข้อผิดพลาดในการส่งสรุป: {e}")
        log_message(f"Error sending summary for ID {practice_id}: {e}", "ERROR")

    if feedback: await ctx.send("\n".join(feedback), ephemeral=True, delete_after=15)

# --- Error Handling (Event) ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound): return
    elif isinstance(error, commands.CheckFailure): # is_correct_channel, has_permissions
        log_message(f"CheckFailure for '{ctx.command}' by {ctx.author}: {error}", "INFO")
        # ข้อความ error ควรถูกส่งจากตัว check เองแล้ว
    elif isinstance(error, commands.MissingRequiredArgument):
        param = error.param.name if error.param else "ข้อมูล"
        await ctx.send(f"⚠️ คุณลืมใส่ `{param}` สำหรับคำสั่งนี้ ดูวิธีใช้ด้วย `{ctx.prefix}help {ctx.command.qualified_name}`", ephemeral=True, delete_after=15)
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"⚠️ ข้อมูลที่คุณป้อนสำหรับคำสั่งนี้ไม่ถูกต้อง ลองดู `{ctx.prefix}help {ctx.command.qualified_name}`", ephemeral=True, delete_after=15)
    else:
        log_message(f"Unhandled error in command '{ctx.command}' by '{ctx.author}': {error}", "ERROR")
        tb_str = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        log_message(f"Traceback:\n{tb_str}", "ERROR")
        try:
            await ctx.send(f"เกิดข้อผิดพลาดที่ไม่คาดคิด: `{error}`. ได้แจ้งผู้ดูแลแล้ว", ephemeral=True, delete_after=15)
        except: pass # Ignore if cannot send feedback

# --- Run Bot ---
DISCORD_BOT_TOKEN = os.getenv('DISCORD_TOKEN')
if not DISCORD_BOT_TOKEN:
    log_message("CRITICAL ERROR: DISCORD_TOKEN environment variable not found. Bot cannot start.", "CRITICAL")
else:
    try:
        log_message("Attempting to run bot...")
        bot.run(DISCORD_BOT_TOKEN)
    except discord.errors.LoginFailure:
        log_message("CRITICAL ERROR: Login Failed. Token is invalid or bot has incorrect intents enabled.", "CRITICAL")
    except discord.errors.PrivilegedIntentsRequired:
        log_message("CRITICAL ERROR: Privileged Intents (Server Members or Message Content) are not enabled in the Discord Developer Portal for this bot.", "CRITICAL")
    except Exception as e_main:
        log_message(f"CRITICAL ERROR during bot.run(): {e_main}", "CRITICAL")
        traceback.print_exc()