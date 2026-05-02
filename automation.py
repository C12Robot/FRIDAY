import os
import subprocess
import webbrowser
import sqlite3
import shutil
import ctypes
from datetime import datetime, timedelta

APPS = {
    "spotify": r"C:\Users\meena\AppData\Roaming\Spotify\Spotify.exe",
    "vs code": r"C:\Users\meena\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "vscode": r"C:\Users\meena\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "browser": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "notepad": "notepad.exe",
    "explorer": "explorer.exe",
    "terminal": "powershell.exe",
    "powershell": "powershell.exe",
    "obsidian": r"C:\Program Files\Obsidian\Obsidian.exe",
}




BLOCKED_SITES = [
    "youtube.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "reddit.com",
    "facebook.com"
]

HOSTS_FILE = r"C:\Windows\System32\drivers\etc\hosts"
focus_mode_active = False

def open_app(app_name):
    try:
        # First check known apps dict
        app = APPS.get(app_name.lower())
        if app:
            subprocess.Popen([app])
            return f"Opening {app_name}."

        # If not in dict, search entire system for it
        search_result = subprocess.run(
            ['where', app_name],
            capture_output=True, text=True
        )
        if search_result.returncode == 0:
            path = search_result.stdout.strip().split('\n')[0]
            subprocess.Popen([path])
            return f"Opening {app_name}."

        # Last resort — use Windows shell (like pressing Win+R)
        subprocess.Popen(f'start "" "{app_name}"', shell=True)
        return f"Attempting to open {app_name}."

    except Exception as e:
        return f"Error opening {app_name}: {str(e)}"

def open_url(url):
    try:
        if not url.startswith("http"):
            url = "https://" + url
        webbrowser.open(url)
        return f"Opened {url} in browser."
    except Exception as e:
        return f"Error opening URL: {str(e)}"

def search_youtube(query):
    url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
    webbrowser.open(url)
    return f"Searching YouTube for: {query}"

def focus_mode_on():
    global focus_mode_active
    try:
        with open(HOSTS_FILE, 'r') as f:
            content = f.read()
        
        additions = ""
        for site in BLOCKED_SITES:
            if site not in content:
                additions += f"\n127.0.0.1 {site}\n127.0.0.1 www.{site}"
        
        if additions:
            with open(HOSTS_FILE, 'a') as f:
                f.write(f"\n# FRIDAY Focus Mode\n{additions}")
        
        focus_mode_active = True
        return "Focus mode on. Distracting sites blocked."
    except PermissionError:
        return "Need admin rights to block sites. Run PowerShell as administrator."
    except Exception as e:
        return f"Focus mode error: {str(e)}"

def focus_mode_off():
    global focus_mode_active
    try:
        with open(HOSTS_FILE, 'r') as f:
            lines = f.readlines()

        cleaned = [line for line in lines
                   if not any(site in line for site in BLOCKED_SITES)
                   and "# FRIDAY Focus Mode" not in line]

        with open(HOSTS_FILE, 'w') as f:
            f.writelines(cleaned)

        focus_mode_active = False
        return "Focus mode off. Sites unblocked."
    except PermissionError:
        return "Need admin rights. Run PowerShell as administrator."
    except Exception as e:
        return f"Focus mode error: {str(e)}"


def search_browser_history(query, limit=5):
    try:
        chrome_history = os.path.expandvars(
            r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\History"
        )

        if not os.path.exists(chrome_history):
            return "Chrome history not found."
        
        temp_copy = os.path.join(os.path.dirname(__file__), "temp_history")
        shutil.copy2(chrome_history, temp_copy)
        
        conn = sqlite3.connect(temp_copy)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT title, url, last_visit_time
            FROM urls
            WHERE title LIKE ? OR url LIKE ?
            ORDER BY last_visit_time DESC
            LIMIT ?
        """, (f"%{query}%", f"%{query}%", limit))
        
        rows = cursor.fetchall()
        conn.close()
        os.remove(temp_copy)
        
        if not rows:
            return f"No history found for: {query}"
        
        results = []
        for title, url, _ in rows:
            results.append(f"• {title}\n  {url}")
        
        return "\n\n".join(results)
    
    except Exception as e:
        print(f"[HISTORY ERROR: {e}]")
        return f"History search error: {str(e)}"

def set_brightness(level):
    try:
        level = max(0, min(100, int(level)))
        import subprocess
        subprocess.run(
            f'powershell -Command "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{level})"',
            shell=True
        )
        return f"Brightness set to {level}%"
    except Exception as e:
        return f"Brightness error: {str(e)}"

def set_volume(level):
    try:
        level = max(0, min(100, int(level)))
        import subprocess
        subprocess.run(
            f'powershell -Command "$obj = New-Object -ComObject WScript.Shell; '
            f'1..50 | ForEach-Object {{ $obj.SendKeys([char]174) }}; '
            f'$steps = [math]::Round({level}/2); '
            f'1..$steps | ForEach-Object {{ $obj.SendKeys([char]175) }}"',
            shell=True
        )
        return f"Volume set to approximately {level}%"
    except Exception as e:
        return f"Volume error: {str(e)}"

def mute_volume():
    try:
        import subprocess
        subprocess.run(
            'powershell -Command "$obj = New-Object -ComObject WScript.Shell; $obj.SendKeys([char]173)"',
            shell=True
        )
        return "Muted."
    except Exception as e:
        return f"Mute error: {str(e)}"

def unmute_volume():
    try:
        import subprocess
        subprocess.run(
            'powershell -Command "$obj = New-Object -ComObject WScript.Shell; $obj.SendKeys([char]173)"',
            shell=True
        )
        return "Unmuted."
    except Exception as e:
        return f"Unmute error: {str(e)}"