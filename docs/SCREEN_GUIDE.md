# Screen Guide - Keep Consumer Running

## Quick Start

### 1. Start Consumer in Screen
```bash
screen -S series-consumer
python consumer.py
```

### 2. Detach (Keeps Running)
Press: `Ctrl+A` then `D`

Your consumer keeps running in the background!

### 3. Reattach Later
```bash
screen -r series-consumer
```

### 4. List All Screen Sessions
```bash
screen -ls
```

### 5. Kill Screen Session
```bash
screen -X -S series-consumer quit
```

## Screen Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+A` then `D` | Detach (keep running) |
| `Ctrl+A` then `C` | Create new window |
| `Ctrl+A` then `N` | Next window |
| `Ctrl+A` then `P` | Previous window |
| `Ctrl+A` then `K` | Kill current window |
| `Ctrl+A` then `?` | Show help |

## Step-by-Step Example

```bash
# 1. Start screen with a name
screen -S consumer

# 2. Run your consumer
python consumer.py

# 3. Detach: Press Ctrl+A, then D
# (You'll see: [detached from consumer])

# 4. Your consumer is still running! Check with:
screen -ls
# Output: There is a screen on: consumer

# 5. Reattach to see logs:
screen -r consumer

# 6. To stop consumer: Press Ctrl+C, then exit screen
# Or kill from outside: screen -X -S consumer quit
```

## Troubleshooting

**"There is no screen to be resumed matching consumer"**
- Screen session doesn't exist or was killed
- Start a new one: `screen -S consumer`

**"There are several suitable screens"**
- Multiple sessions with same name
- List them: `screen -ls`
- Attach specific one: `screen -r <PID>.consumer`

**Consumer stopped after detaching?**
- Check logs for errors
- Make sure you pressed Ctrl+A then D (not just Ctrl+D)
- Try running with auto-restart: `./run_consumer.sh`

## Pro Tips

1. **Name your screens clearly**: `screen -S series-consumer` not just `screen`
2. **Check if running**: `screen -ls` before starting a new one
3. **View without attaching**: `screen -S consumer -X hardcopy /tmp/screen.log && cat /tmp/screen.log`
4. **Auto-start on reboot**: Use systemd or PM2 instead of screen

