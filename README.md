# ⛏️ Solarwakes Launcher

A custom Minecraft launcher built with Python and a web-based UI, featuring user accounts, a friends system, skin support, and offline game launching.

---

## Features

- **Multi-Account Support** — Save and switch between multiple accounts locally
- **User Authentication** — Register and log in with accounts stored in Firebase
- **Friends System** — Search for users, send/accept/decline friend requests, and see online status in real time
- **Skin Manager** — Upload a custom skin PNG and preview your player face in the launcher
- **Version Manager** — Browse, select, and delete installed Minecraft versions and modpacks
- **Game Launcher** — Launch any installed version in offline mode with configurable JVM memory
- **Patch Notes** — In-app changelog panel with categorized tags (fix, feature, perf, security)
- **Custom UI** — Dark pixel-art themed interface built with Tailwind CSS, Eel, and custom fonts

---

## Requirements

- Python 3.8+
- Java (must be on your system `PATH`)
- Google Chrome (Eel uses Chrome to render the UI)
- Minecraft already installed (versions in the default `.minecraft` directory)

---

## Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/yourname/solarwakes-launcher.git
   cd solarwakes-launcher
   ```

2. **Install Python dependencies**

   ```bash
   pip install eel requests Pillow minecraft-launcher-lib
   ```

3. **Project structure**

   ```
   solarwakes-launcher/
   ├── launcher.pyw        # Python/Eel backend
   ├── icon.png            # App icon
   └── web/
       ├── index.html      # Main UI
       ├── style.css       # Custom styles
       └── script.js       # Frontend logic
   ```

   > The `web/` folder must contain `index.html`, `style.css`, and `script.js` — Eel serves them automatically.

4. **Run the launcher**

   ```bash
   python launcher.pyw
   ```

   A Chrome window will open at `1100×700`.

---

## Configuration

At the top of `launcher.pyw` you can adjust:

| Variable | Description |
|---|---|
| `FB_URL` | Your Firebase Realtime Database URL |
| `APP_SECRET` | Salt used when hashing passwords |
| `MC_DIR` | Minecraft directory (auto-detected by default) |
| `SKINS_DIR` | Where custom skin PNGs are stored |
| `SESSION_FILE` | Path to the local session JSON file |

---

## How It Works

- **Backend** (`launcher.pyw`) — A Python script using [Eel](https://github.com/python-eel/Eel) to expose functions to the frontend. Handles auth, session management, game launching, and Firebase communication.
- **Frontend** (`web/`) — A single-page HTML/JS/CSS app. Calls Python functions via `eel.function_name()()` and updates the UI based on responses.
- **Firebase** — Used as a lightweight cloud backend for user accounts, friends, and online status. No Firebase SDK required — the app uses the REST API directly.
- **Game Launch** — Uses [`minecraft-launcher-lib`](https://minecraft-launcher-lib.readthedocs.io/) to build the launch command, then spawns the Java process with offline credentials (UUID derived from username).

---

## Notes

- This launcher operates in **offline/cracked mode**. It does not authenticate with Mojang/Microsoft servers.
- Passwords are hashed with SHA-256 + a local salt before being sent to Firebase. This is not production-grade security — do not reuse passwords.
- The launcher requires Chrome to be installed. It will not open in other browsers by default (Eel limitation).

---

## Dependencies

| Package | Purpose |
|---|---|
| `eel` | Python ↔ Browser bridge |
| `requests` | Firebase REST API calls |
| `Pillow` | Skin image processing |
| `minecraft-launcher-lib` | Building the Minecraft launch command |
| `tkinter` | Native file picker dialog for skin upload |

---

## License

MIT — do whatever you want with it.
