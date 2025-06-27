import requests
import json
import time
import re
import random
import os
import asyncio # Import asyncio for async/await

# --- COLORS FOR CONSOLE OUTPUT ---
class Colors:
    RESET = "\x1b[0m"
    CYAN = "\x1b[36m"
    GREEN = "\x1b[32m"
    YELLOW = "\x1b[33m"
    RED = "\x1b[31m"
    WHITE = "\x1b[37m"
    BOLD = "\x1b[1m"
    BLUE = "\x1b[34m"
    MAGENTA = "\x1b[35m"

# --- CUSTOM LOGGER ---
class Logger:
    def info(self, msg):
        print(f"{Colors.GREEN}[✓] {msg}{Colors.RESET}")

    def warn(self, msg):
        print(f"{Colors.YELLOW}[⚠] {msg}{Colors.RESET}")

    def error(self, msg):
        print(f"{Colors.RED}[✗] {msg}{Colors.RESET}")

    def success(self, msg):
        print(f"{Colors.GREEN}[✅] {msg}{Colors.RESET}")

    def loading(self, msg):
        print(f"{Colors.CYAN}[⟳] {msg}{Colors.RESET}")

    def step(self, msg):
        print(f"{Colors.WHITE}[➤] {msg}{Colors.RESET}")

    def banner(self):
        print(f"{Colors.CYAN}{Colors.BOLD}")
        print('-----------------------------------------------')
        print('  Snoonaut Auto Bot   ')
        print('-----------------------------------------------')
        print(f"{Colors.RESET}\n")

logger = Logger()

# --- CONFIGURATION ---
BASE_API_URL = "https://earn.snoonaut.xyz/api"
COOKIES_FILE = "cookie.txt" # File to load cookies from
PROXIES_FILE = "proxies.txt" # File containing list of proxies (one per line)
WAIT_TIME_SECONDS = 24 * 60 * 60 # 24 hours in seconds for the main loop

# Global variable to store proxy choice
USE_PROXY = False

# --- USER AGENTS ---
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/102.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.5 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 15_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.5 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Mobile Safari/537.36',
]

def get_random_ua():
    return random.choice(USER_AGENTS)

def generate_proof_url():
    """Generates a random X (Twitter) status URL for proof."""
    usernames = ['altcoinbear1', 'cryptofan', 'snootlover', 'airdropking', 'blockchainbro']
    random_status_id = random.randint(1000000000000000000, 9999999999999999999)
    random_username = random.choice(usernames)
    return f"https://x.com/{random_username}/status/{random_status_id}"

def get_proxy_for_request():
    """Reads proxies from proxies.txt and returns a random one, if USE_PROXY is True."""
    global USE_PROXY # Access the global variable
    if not USE_PROXY:
        return None

    if os.path.exists(PROXIES_FILE):
        with open(PROXIES_FILE, 'r') as f:
            proxies_list = [line.strip() for line in f if line.strip()]
        if proxies_list:
            proxy = random.choice(proxies_list)
            # Ensure proxy URL scheme is present for requests library
            if not (proxy.startswith('http://') or proxy.startswith('https://') or proxy.startswith('socks4://') or proxy.startswith('socks5://')):
                logger.warn(f"Proxy '{proxy}' in {PROXIES_FILE} might be missing a scheme. Assuming http://")
                return {'http': f'http://{proxy}', 'https': f'http://{proxy}'}
            else:
                return {'http': proxy, 'https': proxy}
        else:
            logger.warn(f"'{PROXIES_FILE}' is empty. Running without proxy.")
            return None
    else:
        logger.warn(f"'{PROXIES_FILE}' not found. Running without proxy.")
        return None

def load_cookies_from_file():
    """Loads cookies from cookie.txt, one full cookie string per line."""
    cookies = []
    if os.path.exists(COOKIES_FILE):
        with open(COOKIES_FILE, 'r') as f:
            for line in f:
                cookie = line.strip()
                if cookie and not cookie.startswith('#'): # Ignore empty lines and comments
                    cookies.append(cookie)
    return cookies

def create_session(cookie_string):
    """Creates and configures a requests session with common headers and cookie."""
    session = requests.Session()
    session.headers.update({
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.8',
        'Cache-Control': 'max-age=120',
        'Priority': 'u=1, i',
        'Sec-Ch-Ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Brave";v="138"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Gpc': '1',
        'Referer': 'https://earn.snoonaut.xyz/home',
        'User-Agent': get_random_ua(), # Rotate User-Agent for each session
    })
    # Set the entire cookie string
    session.headers['Cookie'] = cookie_string
    return session

async def fetch_user_info(session):
    """Fetches and logs user's profile information."""
    logger.loading('Fetching user info...')
    try:
        proxies_config = get_proxy_for_request() # Use the new function
        response = session.get(f'{BASE_API_URL}/user/stats', proxies=proxies_config, timeout=10)
        response.raise_for_status()
        user_data = response.json().get('user')
        if user_data:
            logger.success('User info fetched successfully')
            logger.info(f"Username: {user_data.get('username')}, Snoot Balance: {user_data.get('snootBalance')}")
            return user_data
        else:
            logger.error('Failed to parse user info from response.')
            return None
    except requests.exceptions.ProxyError as e:
        logger.error(f'Failed to fetch user info: Proxy Error - {e}')
        logger.error('Please check your proxy settings in proxies.txt. Ensure the format is correct (e.g., http://host:port or socks5://user:pass@host:port).')
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f'Failed to fetch user info: {e}')
        return None

async def fetch_tasks(session, task_type):
    """Fetches tasks of a specific type (engagement or referral)."""
    logger.loading(f'Fetching {task_type} tasks...')
    try:
        proxies_config = get_proxy_for_request() # Use the new function
        response = session.get(f'{BASE_API_URL}/tasks?type={task_type}', proxies=proxies_config, timeout=10)
        response.raise_for_status()
        tasks = response.json().get('tasks', [])
        logger.success(f'{task_type} tasks fetched successfully')
        return tasks
    except requests.exceptions.ProxyError as e:
        logger.error(f'Failed to fetch {task_type} tasks: Proxy Error - {e}')
        return []
    except requests.exceptions.RequestException as e:
        logger.error(f'Failed to fetch {task_type} tasks: {e}')
        return []

async def complete_task(session, task):
    """Attempts to complete a given task."""
    logger.loading(f"Attempting to complete task '{task.get('title')}' (ID: {task.get('id')})...")
    payload = {
        "taskId": task.get("id"),
        "action": "complete",
    }

    # Add proofUrl for specific tasks
    if task.get('title') in ['Spread the Snoot!', 'Like, Retweet and Comment']:
        payload['proofUrl'] = generate_proof_url()
        logger.info(f"Generated proof URL for '{task.get('title')}': {payload['proofUrl']}")

    try:
        proxies_config = get_proxy_for_request() # Use the new function
        response = session.post(f'{BASE_API_URL}/tasks/complete', json=payload, proxies=proxies_config, timeout=10)
        response.raise_for_status()
        result = response.json()
        if result.get('success'):
            logger.success(f"Task '{task.get('title')}' completed successfully! Reward: {result.get('reward')} Snoot")
        else:
            logger.warn(f"Task '{task.get('title')}' not completed: {result.get('message', 'Unknown reason')}")
    except requests.exceptions.ProxyError as e:
        logger.error(f"Failed to complete task '{task.get('title')}' (ID: {task.get('id')}): Proxy Error - {e}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to complete task '{task.get('title')}' (ID: {task.get('id')}): {e}")
    time.sleep(random.uniform(2, 5)) # Random delay after each task attempt

async def process_account(cookie_string):
    """Processes all available tasks for a single account."""
    # Display only a snippet of the cookie for privacy/readability
    logger.step(f"Processing account with cookie: {cookie_string[:50]}...")

    session = create_session(cookie_string)

    user_info = await fetch_user_info(session)
    if not user_info:
        logger.error(f"Skipping account due to failure to fetch user info.")
        return

    engagement_tasks = await fetch_tasks(session, 'engagement')
    referral_tasks = await fetch_tasks(session, 'referral')

    all_tasks = engagement_tasks + referral_tasks
    pending_tasks = [task for task in all_tasks if task.get('status') == 'pending']

    if not pending_tasks:
        logger.info("No pending tasks found for this account.")
    else:
        logger.info(f"Found {len(pending_tasks)} pending tasks.")
        for task in pending_tasks:
            await complete_task(session, task)

    logger.success('All tasks processed for this account.')
    time.sleep(random.uniform(5, 10)) # Longer delay between accounts

async def main():
    """Main function to run the Snoonaut bot."""
    logger.banner()
    cookies = load_cookies_from_file()

    if not cookies:
        logger.error(f'No cookies found in {COOKIES_FILE}. Please add your Snoonaut cookie strings to the file, one per line.')
        return

    logger.info(f"Found {len(cookies)} accounts to process.")

    # Proxy selection menu (only ask once at the start)
    global USE_PROXY
    while True:
        choice = input(f"{Colors.YELLOW}Do you want to use proxies? (y/n): {Colors.RESET}").lower().strip()
        if choice == 'y':
            USE_PROXY = True
            logger.info("Bot will attempt to use proxies.")
            break
        elif choice == 'n':
            USE_PROXY = False
            logger.info("Bot will run without proxies.")
            break
        else:
            logger.warn("Invalid choice. Please enter 'y' or 'n'.")

    # --- Start of the main loop ---
    while True:
        logger.step(f"\n--- Starting a new daily cycle (next run in {WAIT_TIME_SECONDS / 3600:.1f} hours) ---")
        
        for i, cookie_string in enumerate(cookies):
            logger.step(f"\n--- Starting processing for Account #{i+1} ---")
            await process_account(cookie_string)
            logger.step(f"--- Finished processing for Account #{i+1} ---")

        logger.success('All accounts processed for this cycle.')
        
        # Calculate time to wait until the next cycle
        current_time = time.time()
        # You could also try to align it to a specific time of day here if needed
        # For simplicity, we just wait for the full WAIT_TIME_SECONDS
        
        logger.info(f"Waiting for {WAIT_TIME_SECONDS / 3600:.1f} hours before next cycle...")
        time.sleep(WAIT_TIME_SECONDS)
        # --- End of the main loop ---

if __name__ == "__main__":
    asyncio.run(main())
