#!/bin/bash
# Discord Habit Bot Management Script
# Usage: ./manage-bot.sh {start|stop|restart|status|logs|install-service|remove-service}

BOT_DIR="/home/ian/scripts/discord-buddy"
SERVICE_NAME="discord-habit-bot"
CONDA_ENV="habit-bot"

case "$1" in
    start)
        echo "🚀 Starting Discord Habit Bot..."
        cd "$BOT_DIR"
        source /home/ian/miniconda3/etc/profile.d/conda.sh
        conda activate "$CONDA_ENV"
        
        # Check if running as service
        if systemctl is-active --quiet "$SERVICE_NAME"; then
            echo "Bot is running as systemd service. Use 'sudo systemctl start $SERVICE_NAME' instead."
        else
            nohup python bot.py > logs/bot_output.log 2>&1 &
            echo $! > bot.pid
            echo "✅ Bot started in background (PID: $(cat bot.pid))"
            echo "📄 Logs: tail -f $BOT_DIR/logs/bot_output.log"
        fi
        ;;
        
    stop)
        echo "🛑 Stopping Discord Habit Bot..."
        if systemctl is-active --quiet "$SERVICE_NAME"; then
            echo "Bot is running as systemd service. Use 'sudo systemctl stop $SERVICE_NAME' instead."
        else
            if [ -f bot.pid ]; then
                PID=$(cat bot.pid)
                kill $PID 2>/dev/null && echo "✅ Bot stopped (PID: $PID)" || echo "❌ Bot was not running"
                rm -f bot.pid
            else
                pkill -f "python bot.py" && echo "✅ Bot processes stopped" || echo "❌ No bot processes found"
            fi
        fi
        ;;
        
    restart)
        $0 stop
        sleep 2
        $0 start
        ;;
        
    status)
        echo "📊 Discord Habit Bot Status:"
        if systemctl is-active --quiet "$SERVICE_NAME"; then
            echo "🟢 Running as systemd service"
            systemctl status "$SERVICE_NAME" --no-pager -l
        elif [ -f bot.pid ] && kill -0 $(cat bot.pid) 2>/dev/null; then
            echo "🟢 Running in background (PID: $(cat bot.pid))"
        else
            echo "🔴 Not running"
        fi
        ;;
        
    logs)
        echo "📄 Bot Logs (press Ctrl+C to exit):"
        if systemctl is-active --quiet "$SERVICE_NAME"; then
            journalctl -u "$SERVICE_NAME" -f
        else
            tail -f logs/bot_output.log logs/habit_bot.log 2>/dev/null || echo "No log files found"
        fi
        ;;
        
    install-service)
        echo "🔧 Installing systemd service..."
        
        # Create service file
        sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null << EOF
[Unit]
Description=Discord Habit Bot - Gamified Habit Tracking
After=network.target
Wants=network.target

[Service]
Type=simple
User=ian
Group=ian
WorkingDirectory=$BOT_DIR
Environment=PATH=/home/ian/miniconda3/envs/$CONDA_ENV/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/home/ian/miniconda3/envs/$CONDA_ENV/bin/python bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

        # Reload systemd and enable service
        sudo systemctl daemon-reload
        sudo systemctl enable "$SERVICE_NAME"
        
        echo "✅ Service installed and enabled"
        echo "🚀 Start with: sudo systemctl start $SERVICE_NAME"
        ;;
        
    remove-service)
        echo "🗑️ Removing systemd service..."
        sudo systemctl stop "$SERVICE_NAME" 2>/dev/null
        sudo systemctl disable "$SERVICE_NAME" 2>/dev/null
        sudo rm -f "/etc/systemd/system/$SERVICE_NAME.service"
        sudo systemctl daemon-reload
        echo "✅ Service removed"
        ;;
        
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|install-service|remove-service}"
        echo ""
        echo "Commands:"
        echo "  start           - Start bot in background"
        echo "  stop            - Stop bot"
        echo "  restart         - Restart bot"
        echo "  status          - Show bot status"
        echo "  logs            - Show bot logs (follow)"
        echo "  install-service - Install as systemd service (recommended)"
        echo "  remove-service  - Remove systemd service"
        echo ""
        echo "For systemd service management:"
        echo "  sudo systemctl start/stop/restart $SERVICE_NAME"
        echo "  sudo systemctl status $SERVICE_NAME"
        echo "  journalctl -u $SERVICE_NAME -f"
        exit 1
        ;;
esac