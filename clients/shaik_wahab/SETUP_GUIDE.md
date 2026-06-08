# LinkedIn Agent Setup Guide — Shaik Wahab

Follow every step in order. Do not skip anything.

---

## Step 1 — Open Terminal

Press **Cmd + Space** on your keyboard to open Spotlight Search.

Type **Terminal** and press Enter.

A black or white window with a blinking cursor will open. That is Terminal. Leave it open for the whole setup.

---

## Step 2 — Run the setup command

Copy and paste this entire line into Terminal and press Enter:

```
curl -sSL https://raw.githubusercontent.com/savas-web/linkedin-agent-2/main/setup.sh | bash -s shaik_wahab REPLACE_WITH_YOUR_ANTHROPIC_KEY
```

This will take a few minutes. You will see text moving on the screen. That is normal. Wait until it stops and you see a message that says something like **"Almost there!"** or **"All done!"**

If it asks you for your Mac password at any point, type it in and press Enter. You will not see the password as you type — that is normal.

---

## Step 3 — Add your two config files

You will have received two files from your account manager:

- **config.json**
- **system_prompt.txt**

You need to place both files into this folder on your Mac:

```
/Users/YOUR_NAME/Desktop/linkedin-agent-2/clients/shaik_wahab/
```

To get there:

1. Open **Finder**
2. Click **Desktop** on the left side
3. Open the folder called **linkedin-agent-2**
4. Open the folder called **clients**
5. Open the folder called **shaik_wahab**
6. Drag both files into this folder

---

## Step 4 — Finish the installation

Go back to Terminal and paste this in, then press Enter:

```
cd ~/Desktop/linkedin-agent-2 && bash install_client.sh shaik_wahab && bash install_updater.sh shaik_wahab
```

Wait for it to finish. When you see **"Agent installed and running"** and **"Auto-updater installed"** you are good.

---

## Step 5 — Log into LinkedIn

A Chrome window will open automatically.

Log into LinkedIn as you normally would. Use your usual email and password.

Once you are logged in, you do not need to do anything else. Just leave the window open. You can minimise it.

---

## Step 6 — Check Telegram

Open the Telegram group your account manager added you to.

Within a few minutes you should see the agent send its first approval notification. It will look something like this:

```
🎖 LinkedIn Agent
📩 New LinkedIn DM
From: John Smith

Their message:
Hey Shaik, great to connect...

Proposed reply:
Hey John, thanks for connecting...

[✅ Approve]  [✏️ Edit]  [⏭️ Skip]  [❌ Cancel]
```

Tap **Approve** to send the message or **Edit** to change it before sending.

---

## You are done

The agent is now running in the background. You do not need to keep Terminal open. Your Mac just needs to be on and connected to the internet.

---

## Quick reference

| What you want to do | What to run in Terminal |
|---|---|
| Start the agent manually | `cd ~/Desktop/linkedin-agent-2 && source venv/bin/activate && python main.py shaik_wahab` |
| Stop the agent | `launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/digital.rooney.shaik_wahab.plist` |
| Restart the agent | `launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/digital.rooney.shaik_wahab.plist && launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/digital.rooney.shaik_wahab.plist` |

---

## Something not working?

Send a screenshot of the Terminal to your account manager and they will sort it out.
