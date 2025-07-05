import os
import random
import time
from dotenv import load_dotenv
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from colorama import init, Fore, Style
from inquirerpy import inquirer
from pathlib import Path
import re
# import json # No longer needed if _vcrcs metadata is not stored in JSON

# Import Anti-Captcha library
from anticaptchaofficial.antigatetask import *

# Initialize colorama for colored output
init()

# Colors and Logger
class Colors:
    RESET = Style.RESET_ALL
    CYAN = Fore.CYAN
    GREEN = Fore.GREEN
    YELLOW = Fore.YELLOW
    RED = Fore.RED
    WHITE = Fore.WHITE
    BOLD = Style.BRIGHT
    BLUE = Fore.BLUE
    MAGENTA = Fore.MAGENTA

class Logger:
    @staticmethod
    def info(msg):
        print(f"{Colors.GREEN}[✓] {msg}{Colors.RESET}")

    @staticmethod
    def warn(msg):
        print(f"{Colors.YELLOW}[⚠] {msg}{Colors.RESET}")

    @staticmethod
    def error(msg):
        print(f"{Colors.RED}[✗] {msg}{Colors.RESET}")

    @staticmethod
    def success(msg):
        print(f"{Colors.GREEN}[✅] {msg}{Colors.RESET}")

    @staticmethod
    def loading(msg):
        print(f"{Colors.CYAN}[⟳] {msg}{Colors.RESET}")

    @staticmethod
    def step(msg):
        print(f"{Colors.WHITE}[➤] {msg}{Colors.RESET}")

    @staticmethod
    def banner():
        print(f"{Colors.CYAN}{Colors.BOLD}")
        print("-----------------------------------------------")
        print("  Snoonaut Auto Bot - ADB PYTHON  ")
        print("-----------------------------------------------")
        print(f"{Colors.RESET}\n")

# --- CONFIGURATION ---
BASE_API_URL = "https://earn.snoonaut.xyz/api"
COOKIES_FILE = "cookie.txt" # File ini sekarang hanya untuk cookie sesi akun Anda
PROXIES_FILE = "proxies.txt"

# Anti-Captcha Configuration
ANTICAPTCHA_KEY_FILE = "anticaptcha.key"
SNOONAUT_BASE_URL = "https://earn.snoonaut.xyz/"

# Global variable to store proxy choice
USE_PROXY = False

# Global variables for consistent session details after Anti-Captcha bypass
# These are only valid for the *current* bypass attempt, not persisted
CURRENT_BYPASS_USER_AGENT = None # Renamed for clarity: reflects UA from latest successful bypass
CURRENT_BYPASS_PROXY = None # Renamed for clarity: reflects proxy from latest successful bypass

# --- USER AGENTS ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
]

def get_random_ua():
    return random.choice(USER_AGENTS)

def generate_proof_url():
    usernames = ["altcoinbear1", "cryptofan", "snootlover", "airdropking", "blockchainbro"]
    random_status_id = random.randint(1000000000000000000, 1900000000000000000)
    random_username = random.choice(usernames)
    return f"https://x.com/{random_username}/status/{random_status_id}"

# Proxy Agent (Prioritize CURRENT_BYPASS_PROXY if it exists for consistency)
def get_proxy():
    global USE_PROXY, CURRENT_BYPASS_PROXY # Use the new global name
    if not USE_PROXY:
        return None
    
    # Prioritaskan proxy yang terakhir berhasil digunakan oleh Anti-Captcha di bypass terakhir
    if CURRENT_BYPASS_PROXY:
        proxy = CURRENT_BYPASS_PROXY
        if not (proxy.startswith("http") or proxy.startswith("socks")):
            return {"http": f"http://{proxy}", "https": f"http://{proxy}"}
        else:
            return {"http": proxy, "https": proxy}

    # Fallback ke proxy acak dari file jika CURRENT_BYPASS_PROXY tidak disetel
    if Path(PROXIES_FILE).exists():
        with open(PROXIES_FILE, "r", encoding="utf-8") as f:
            proxies = [line.strip() for line in f if line.strip()]
        if proxies:
            proxy = random.choice(proxies)
            if not proxy.startswith(("http", "socks")):
                proxy = f"http://{proxy}"
            return {"http": proxy, "https": proxy}
    
    Logger.warn(f"'{PROXIES_FILE}' not found or empty. Running without proxy (or using system default if no bypass proxy is available).")
    return None

# Load Account Session Cookies (simplified)
def load_account_session_cookies():
    session_cookies = []
    if Path(COOKIES_FILE).exists():
        with open(COOKIES_FILE, 'r') as f:
            for line in f:
                cookie = line.strip()
                if cookie and not cookie.startswith('#'):
                    session_cookies.append(cookie)
    Logger.info(f"Loaded {len(session_cookies)} account session cookies from {COOKIES_FILE}.")
    return session_cookies

# No save_all_cookies_to_file or save_cookies_to_file anymore as _vcrcs is not persisted

def load_anticaptcha_key():
    if Path(ANTICAPTCHA_KEY_FILE).exists():
        with open(ANTICAPTCHA_KEY_FILE, 'r') as f:
            key = f.readline().strip()
            if key:
                Logger.info(f"Anti-Captcha key loaded from {ANTICAPTCHA_KEY_FILE}.")
                return key
            else:
                Logger.error(f"File {ANTICAPTCHA_KEY_FILE} is empty. Please put your Anti-Captcha key in it.")
                return None
    else:
        Logger.error(f"Anti-Captcha key file '{ANTICAPTCHA_KEY_FILE}' not found. Please create it and put your key in it.")
        return None

# Create Requests Session (now receives _vcrcs_cookie_value and specific_user_agent)
def create_session(account_session_cookie, vcrcs_cookie_value=None, specific_user_agent=None):
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))
    
    # Gabungkan cookie sesi akun dengan cookie _vcrcs jika ada
    full_cookie_string = account_session_cookie
    if vcrcs_cookie_value:
        # Penting: Pastikan _vcrcs yang lama dihapus jika ada di account_session_cookie (ini tidak seharusnya terjadi jika cookie.txt hanya berisi cookie sesi akun)
        # Atau jika string cookie itu sendiri hasil dari bypass sebelumnya.
        full_cookie_string = re.sub(r'_vcrcs=[^;]*;?\s*', '', full_cookie_string) # Hapus _vcrcs lama jika ada
        full_cookie_string = f"_vcrcs={vcrcs_cookie_value}; {full_cookie_string}".strip('; ') # Gabungkan dan bersihkan
    
    # Set User-Agent
    user_agent_to_use = specific_user_agent if specific_user_agent else get_random_ua()

    session.headers.update({
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "cache-control": "no-cache",
        "priority": "u=1, i",
        "sec-ch-ua": '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"', # Ini bisa diganti dinamis dari fingerprint
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "cookie": full_cookie_string, # Gunakan gabungan cookie
        "Referer": "https://earn.snoonaut.xyz/home",
        "User-Agent": user_agent_to_use,
    })
    return session

# --- FUNGSI UNTUK BYPASS ANTI-BOT MENGGUNAKAN ANTI-CAPTCHA ---
def bypass_anti_bot_with_anticaptcha(api_key, retries=3, initial_delay=10):
    global CURRENT_BYPASS_USER_AGENT, CURRENT_BYPASS_PROXY # Declare globals here

    if not api_key:
        Logger.error("Anti-Captcha API key tidak tersedia. Tidak dapat bypass anti-bot.")
        return None # Indicate failure

    for attempt in range(retries):
        Logger.loading(f"Mencoba melewati layar anti-bot menggunakan Anti-Captcha (Percobaan {attempt + 1}/{retries})...")
        solver = antigateTask()
        solver.set_verbose(1)
        solver.set_key(api_key)
        solver.set_website_url(SNOONAUT_BASE_URL)
        solver.set_template_name("Anti-bot screen bypass")
        solver.set_variables({
            "css_selector": "#header-text" # CSS Selector yang telah diidentifikasi
        })

        current_attempt_proxy = None # Local variable for this attempt's proxy
        proxies_config = get_proxy() # Get a proxy (prioritizing CURRENT_BYPASS_PROXY if set)
        if proxies_config:
            proxy_url = list(proxies_config.values())[0] # Get the raw proxy string
            current_attempt_proxy = proxy_url # Store for logging/return if successful
            
            proxy_type = "http"
            if "socks5://" in proxy_url:
                proxy_type = "socks5"
            elif "socks4://" in proxy_url:
                proxy_type = "socks4"
            elif "https://" in proxy_url:
                proxy_type = "http" # Fallback, as antigate might not support "https" proxy type directly
                Logger.warn("Proxy HTTPS mungkin tidak didukung langsung oleh Antigate. Menggunakan 'http' sebagai fallback type.")

            parsed_proxy = re.sub(r'https?://|socks[45]?://', '', proxy_url)
            
            try:
                proxy_parts = parsed_proxy.split('@')
                if len(proxy_parts) > 1: # Has username and password
                    auth_parts = proxy_parts[0].split(':')
                    host_port_parts = proxy_parts[1].split(':')
                    
                    solver.set_proxy_login(auth_parts[0])
                    solver.set_proxy_password(auth_parts[1])
                    solver.set_proxy_address(host_port_parts[0])
                    solver.set_proxy_port(int(host_port_parts[1]))
                else: # No username and password
                    host_port_parts = parsed_proxy.split(':')
                    solver.set_proxy_address(host_port_parts[0])
                    solver.set_proxy_port(int(host_port_parts[1]))

                solver.set_proxy_type(proxy_type)
                Logger.info(f"Menggunakan proxy {proxy_type.upper()} via Anti-Captcha: {parsed_proxy}")
            except (IndexError, ValueError) as e:
                Logger.error(f"Format proxy tidak valid: '{proxy_url}'. Error: {e}. Melewati percobaan ini.")
                time.sleep(initial_delay * (attempt + 1))
                continue # Skip to next retry attempt

        result = solver.solve_and_return_solution()

        if result != 0:
            Logger.success("Sistem anti-bot berhasil dilewati!")
            cookies_dict = result["cookies"]
            
            # Extract _vcrcs cookie
            vcrcs_cookie_value = cookies_dict.get("_vcrcs")
            
            # Extract User-Agent from fingerprint, fallback to random_ua if not found
            used_user_agent = result["fingerprint"].get("self.navigator.userAgent", get_random_ua()) 
            
            if vcrcs_cookie_value:
                Logger.info(f"Cookie _vcrcs yang didapat: {vcrcs_cookie_value[:50]}...")
            if used_user_agent:
                Logger.info(f"User-Agent yang digunakan oleh Anti-Captcha: {used_user_agent}")
            if current_attempt_proxy:
                Logger.info(f"Proxy yang digunakan oleh Anti-Captcha: {current_attempt_proxy}")

            # Update global variables for session consistency
            CURRENT_BYPASS_USER_AGENT = used_user_agent
            CURRENT_BYPASS_PROXY = current_attempt_proxy

            return vcrcs_cookie_value # Return only _vcrcs_cookie value
        else:
            error_msg = f"Gagal melewati sistem anti-bot: {solver.error_code}"
            Logger.error(error_msg)
            if "ERROR_NO_SLOT_AVAILABLE" in solver.error_code:
                if attempt < retries - 1:
                    wait_time = initial_delay * (attempt + 1)
                    Logger.warn(f"Tidak ada worker tersedia. Menunggu {wait_time} detik sebelum mencoba lagi...")
                    time.sleep(wait_time)
                else:
                    Logger.error("Semua percobaan habis. Tidak dapat mendapatkan cookie _vcrcs baru.")
            elif "ERROR_ZERO_BALANCE" in solver.error_code:
                Logger.error("Saldo Anti-Captcha Anda nol. Isi ulang akun Anda. Tidak akan mencoba lagi.")
                return None # Fatal error, stop immediately
            else:
                Logger.error(f"Error Anti-Captcha tak terduga: {solver.error_code}. Tidak akan mencoba lagi.")
            return None # Indicate failure

    return None # All retries failed

# Fetch User Info
def fetch_user_info(session):
    Logger.loading("Fetching user info...")
    time.sleep(random.uniform(1, 3)) # Add random delay
    try:
        proxies = get_proxy() # Will use CURRENT_BYPASS_PROXY if set
        response = session.get(
            "https://earn.snoonaut.xyz/api/user/stats",
            proxies=proxies,
            timeout=15
        )
        response.raise_for_status()
        data = response.json()
        Logger.success("User info fetched successfully")
        Logger.info(f"Username: {data['user']['username']}, Snoot Balance: {data['user']['snootBalance']}")
        return data
    except requests.exceptions.RequestException as e:
        Logger.error(f"Failed to fetch user info: {e}")
        # Return status code for specific handling
        if hasattr(e.response, "status_code"):
            return {"status_code": e.response.status_code}
        return None

# Fetch Tasks
def fetch_tasks(session, task_type):
    Logger.loading(f"Fetching {task_type} tasks...")
    time.sleep(random.uniform(1, 3)) # Add random delay
    try:
        proxies = get_proxy() # Will use CURRENT_BYPASS_PROXY if set
        response = session.get(
            f"https://earn.snoonaut.xyz/api/tasks?type={task_type}",
            proxies=proxies,
            timeout=15
        )
        response.raise_for_status()
        data = response.json()
        Logger.success(f"{task_type} tasks fetched successfully")
        return data.get("tasks", [])
    except requests.exceptions.RequestException as e:
        Logger.error(f"Failed to fetch {task_type} tasks: {e}")
        # Return status code for specific handling
        if hasattr(e.response, "status_code"):
            return {"status_code": e.response.status_code}
        return []

# Generate Proof URL
def generate_proof_url():
    usernames = ["altcoinbear1", "cryptofan", "snootlover", "airdropking", "blockchainbro"]
    random_status_id = random.randint(1000000000000000000, 1900000000000000000)
    random_username = random.choice(usernames)
    return f"https://x.com/{random_username}/status/{random_status_id}"

# Complete Task
def complete_task(session, task):
    Logger.loading(f"Completing task {task['title']} ({task['id']})...")
    time.sleep(random.uniform(2, 5)) # Add random delay
    try:
        payload = {"taskId": task["id"], "action": "complete"}
        if task["title"] in ["Spread the Snoot!", "Like, Retweet and Comment"]:
            payload["proofUrl"] = generate_proof_url()
            Logger.info(f"Generated proof URL for '{task['title']}': {payload['proofUrl']}")
        
        proxies = get_proxy() # Will use CURRENT_BYPASS_PROXY if set
        response = session.post(
            "https://earn.snoonaut.xyz/api/tasks/complete",
            json=payload,
            headers={"content-type": "application/json"}, # User-Agent already in session headers
            proxies=proxies,
            timeout=15
        )
        response.raise_for_status()
        data = response.json()
        if data.get("success"):
            Logger.success(f"Task {task['title']} completed, Reward: {data.get('reward')}")
            return True # Indicate success
        else:
            Logger.warn(f"Task {task['title']} not completed: {data.get('message', 'Unknown reason')}")
            return False
    except requests.exceptions.RequestException as e:
        Logger.error(f"Failed to complete task {task['title']} ({task['id']}): {e}")
        # Return status code for specific handling
        if hasattr(e.response, "status_code"):
            return {"status_code": e.response.status_code}
        return False

# Perform Daily Check-in Function
def perform_daily_check_in(session): # cookie parameter removed, session already has it
    Logger.loading("Performing daily check-in...")
    time.sleep(random.uniform(1, 3)) # Delay to avoid bot detection
    try:
        proxies = get_proxy()
        response = session.post(
            "https://earn.snoonaut.xyz/api/checkin",
            json={},
            headers={"content-type": "application/json"}, # User-Agent already in session headers
            proxies=proxies,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        if data.get("success"):
            Logger.success(f"Daily check-in completed. Reward: {data.get('reward', 'N/A')}")
            return True # Indicate success
        else:
            Logger.warn("Daily check-in already completed or not available")
            return True # Still considered successful, just already done
    except requests.exceptions.RequestException as e:
        Logger.error(f"Failed to perform daily check-in: {e}")
        if hasattr(e.response, "status_code"):
            return {"status_code": e.response.status_code}
        return False # Indicate failure


# Process Account
async def process_account(account_session_cookie, mode, anticaptcha_key):
    global CURRENT_BYPASS_USER_AGENT, CURRENT_BYPASS_PROXY # Declare globals

    Logger.step(f"Processing account with base cookie: {account_session_cookie[:50]}...")
    
    # Dapatkan _vcrcs_cookie dan User-Agent/Proxy terbaru dari Anti-Captcha di setiap awal akun
    # (Ini adalah perubahan kunci: _vcrcs selalu baru per akun)
    vcrcs_cookie_value = None
    
    # Panggil bypass_anti_bot_with_anticaptcha untuk mendapatkan _vcrcs yang segar
    vcrcs_cookie_value = bypass_anti_bot_with_anticaptcha(anticaptcha_key)
    
    if not vcrcs_cookie_value:
        Logger.error("Failed to obtain a valid _vcrcs cookie. Skipping account.")
        return # Cannot proceed without a valid _vcrcs

    # User-Agent dan Proxy global sudah di-update di dalam bypass_anti_bot_with_anticaptcha
    # Gunakan mereka untuk sesi ini
    session = create_session(account_session_cookie, vcrcs_cookie_value, CURRENT_BYPASS_USER_AGENT)
    
    # Coba fetch user info dengan sesi yang sudah lengkap
    user_info_result = fetch_user_info(session)
    
    # Jika masih gagal setelah mendapatkan _vcrcs baru, ada masalah lain (misal IP diblokir)
    if user_info_result and user_info_result.get("status_code") in [403, 429]:
        Logger.error(f"User info fetch failed (Status {user_info_result['status_code']}) even with new _vcrcs. Skipping account.")
        return
    elif not user_info_result: # General error, not 403/429
        Logger.error("General error fetching user info. Skipping account.")
        return

    # Lanjutkan dengan mode yang dipilih (daily check-in atau tasks)
    if mode == "daily":
        check_in_result = perform_daily_check_in(session)
        if isinstance(check_in_result, dict) and check_in_result.get("status_code") in [401, 403, 429]:
            Logger.error("Daily check-in failed, likely due to session issue. Skipping check-in for this account.")
            # Note: We don't re-bypass here because we already did it at the start of process_account.
            # If it still fails, the problem is persistent for this proxy/UA combo.
    elif mode == "tasks":
        engagement_tasks = fetch_tasks(session, "engagement")
        referral_tasks = fetch_tasks(session, "referral")
        
        # Check if fetch_tasks returned an error dict instead of list
        if isinstance(engagement_tasks, dict) and engagement_tasks.get("status_code") in [401, 403, 429] or \
           isinstance(referral_tasks, dict) and referral_tasks.get("status_code") in [401, 403, 429]:
            Logger.error("Task fetch failed, likely due to session issue. Cannot fetch tasks for this account.")
            return # Exit if still fails after getting fresh _vcrcs
        
        engagement_tasks = engagement_tasks if isinstance(engagement_tasks, list) else []
        referral_tasks = referral_tasks if isinstance(referral_tasks, list) else []

        all_tasks = engagement_tasks + referral_tasks
        pending_tasks = [task for task in all_tasks if task.get("status") == "pending"]
        
        if not pending_tasks:
            Logger.info("No pending tasks found for this account.")
        else:
            Logger.info(f"Found {len(pending_tasks)} pending tasks.")
            for task in pending_tasks:
                task_completion_result = complete_task(session, task)
                if isinstance(task_completion_result, dict) and task_completion_result.get("status_code") in [401, 403, 429]:
                    Logger.error("Task completion failed, likely due to session issue. Cannot complete task for this account.")
                    # Again, no re-bypass here as it was already done.
                time.sleep(random.uniform(2, 5)) # Delay after each task

    Logger.success("Account processing completed")

# Prompt User for Mode
def prompt_user():
    questions = [
        {
            "type": "list",
            "name": "mode",
            "message": "What would you like to do?",
            "choices": ["Perform Daily Check-in", "Complete Tasks"],
        },
        {
            "type": "confirm",
            "name": "run_daily_with_timer",
            "message": "Would you like to schedule Daily Check-in to run every 24 hours?",
            "when": lambda answers: answers["mode"] == "Perform Daily Check-in",
            "default": False
        }
    ]
    answers = inquirer.prompt(questions)
    if answers and answers["mode"] == "Perform Daily Check-in":
        answers["mode"] = "daily"
    elif answers and answers["mode"] == "Complete Tasks":
        answers["mode"] = "tasks"
    return answers
    
# Main Function
def main():
    Logger.banner()
    
    # Load Anti-Captcha key once at startup
    anticaptcha_api_key = load_anticaptcha_key()
    if not anticaptcha_api_key:
        Logger.error("Anti-Captcha API key not available. Exiting.")
        return

    # Load account session cookies from cookie.txt
    account_session_cookies = load_account_session_cookies()
    if not account_session_cookies:
        Logger.error("No account session cookies found in cookie.txt. Please add them, one per line.")
        return
    
    answers = prompt_user()
    if not answers:
        Logger.error("User cancelled the prompt. Exiting...")
        return
    
    mode = answers["mode"]
    run_daily_with_timer = answers.get("run_daily_with_timer", False)
    
    # Run immediately for all accounts
    Logger.step("Starting initial run for all accounts...")
    for i, cookie in enumerate(account_session_cookies):
        Logger.step(f"--- Processing Account #{i+1} ---")
        process_account(cookie, mode, anticaptcha_api_key) # Pass anticaptcha_key
        time.sleep(random.uniform(5, 10)) # Delay between accounts

    # Set up timer for daily check-in if selected
    if mode == "daily" and run_daily_with_timer:
        DAILY_INTERVAL = 24 * 60 * 60  # 24 hours in seconds
        Logger.info("Daily check-in scheduled to run every 24 hours.")
        while True:
            Logger.banner()
            Logger.info("Running scheduled daily check-in...")
            for i, cookie in enumerate(account_session_cookies):
                Logger.step(f"--- Processing Account #{i+1} (Scheduled Run) ---")
                process_account(cookie, "daily", anticaptcha_api_key) # Pass anticaptcha_key
                time.sleep(random.uniform(5, 10)) # Delay between accounts
            time.sleep(DAILY_INTERVAL)
            
    Logger.success("Bot finished all operations.")

if __name__ == "__main__":
    try:
        load_dotenv() 
        main()
    except Exception as e:
        Logger.error(f"Main process failed: {e}")
