# How to Keep Consumer Running

## Quick Answer: You DON'T Need 5-10 Consumers!

**One consumer is enough!** Kafka automatically handles message distribution. Running multiple consumers in the same consumer group just splits the work - it doesn't make messages more reliable.

## How Many Consumers Do You Need?

- **1 consumer** = Perfect for hackathon (handles all messages)
- **2 consumers** = Good if you and teammate both want to run it (load balancing)
- **5-10 consumers** = Unnecessary unless you have 5-10 partitions (you probably have 1-2)

**Rule:** Number of consumers ≤ Number of partitions

## Ways to Keep It Running

### Option 1: Screen (Simple, Good for Testing)
```bash
# Install screen (if not installed)
# macOS: already installed
# Linux: sudo apt-get install screen

# Start consumer in screen
screen -S series-consumer
python consumer.py

# Detach: Press Ctrl+A, then D
# Reattach: screen -r series-consumer
# Kill: screen -X -S series-consumer quit
```

### Option 2: Tmux (Better Alternative)
```bash
# Install tmux (if not installed)
# macOS: brew install tmux
# Linux: sudo apt-get install tmux

# Start consumer in tmux
tmux new -s series-consumer
python consumer.py

# Detach: Press Ctrl+B, then D
# Reattach: tmux attach -t series-consumer
# Kill: tmux kill-session -t series-consumer
```

### Option 3: Run Script (Auto-Restart)
```bash
chmod +x run_consumer.sh
./run_consumer.sh
```

### Option 4: PM2 (Production-Grade)
```bash
# Install PM2
npm install -g pm2

# Start consumer
pm2 start consumer.py --name series-consumer --interpreter python3

# View logs
pm2 logs series-consumer

# Stop
pm2 stop series-consumer

# Auto-start on reboot
pm2 startup
pm2 save
```

### Option 5: Systemd (Linux Only)
Create `/etc/systemd/system/series-consumer.service`:
```ini
[Unit]
Description=Series Hackathon Consumer
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/Series
ExecStart=/usr/bin/python3 /path/to/Series/consumer.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable series-consumer
sudo systemctl start series-consumer
sudo systemctl status series-consumer
```

### Option 6: Cloud Deployment (Best for Production)
- **AWS EC2** with systemd
- **Google Cloud Run** (serverless)
- **Heroku** (easy deployment)
- **Railway** (simple setup)

## Recommended for Hackathon

**Use Screen or Tmux** - Simple and works great:

```bash
# Start
screen -S consumer
python consumer.py

# Detach (keeps running): Ctrl+A, then D
# Reattach later: screen -r consumer
```

## What Happens with Multiple Consumers?

If you and your teammate both run `consumer.py`:

✅ **Same Consumer Group** (from `.env`):
- Kafka distributes partitions between you
- Each consumer processes different messages
- No duplicates
- **This is GOOD!**

❌ **Different Consumer Groups**:
- Both process ALL messages
- Duplicate responses sent
- **This is BAD!**

## Check How Many Partitions You Have

When consumer starts, it shows:
```
📊 Topic has X partition(s)
📊 Assigned partitions: [0]
```

If you see 1 partition, you only need 1 consumer.
If you see 2 partitions, you can use 2 consumers (one per partition).

## Summary

- **1 consumer is enough** for a hackathon
- Use **screen** or **tmux** to keep it running
- Don't run 5-10 consumers unless you have 5-10 partitions
- Kafka handles message distribution automatically

