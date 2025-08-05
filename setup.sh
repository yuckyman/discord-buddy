#!/bin/bash
#
# Discord Habit Bot Setup Script
# 
# This script sets up the Discord Habit Bot from scratch on a Debian/Ubuntu system.
# It handles conda installation, environment setup, database initialization, and systemd service configuration.
#
# Usage: sudo ./setup.sh
#

set -e  # Exit on any error

# Configuration
BOT_USER="habitbot"
BOT_GROUP="habitbot"
INSTALL_DIR="/opt/discord-habit-bot"
CONDA_INSTALL_DIR="/opt/miniconda3"
ENV_NAME="habit-bot"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   error "This script must be run as root (use sudo)"
   exit 1
fi

log "Starting Discord Habit Bot setup..."

# Update system packages
log "Updating system packages..."
apt update && apt upgrade -y

# Install required system packages
log "Installing system dependencies..."
apt install -y \
    curl \
    wget \
    git \
    sudo \
    systemctl \
    build-essential \
    python3-dev \
    sqlite3

# Create user and group for the bot
log "Creating bot user and group..."
if ! id "$BOT_USER" &>/dev/null; then
    groupadd "$BOT_GROUP"
    useradd -r -g "$BOT_GROUP" -d "$INSTALL_DIR" -s /bin/bash "$BOT_USER"
    success "Created user: $BOT_USER"
else
    warn "User $BOT_USER already exists"
fi

# Create installation directory
log "Creating installation directory..."
mkdir -p "$INSTALL_DIR"
chown "$BOT_USER:$BOT_GROUP" "$INSTALL_DIR"

# Install Miniconda (idempotent)
if [ ! -d "$CONDA_INSTALL_DIR" ]; then
    log "Installing Miniconda..."
    wget -q https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh
    bash /tmp/miniconda.sh -b -p "$CONDA_INSTALL_DIR"
    chown -R "$BOT_USER:$BOT_GROUP" "$CONDA_INSTALL_DIR"
    rm /tmp/miniconda.sh
    success "Miniconda installed"
else
    warn "Miniconda already installed at $CONDA_INSTALL_DIR"
fi

# Set up conda environment
log "Setting up conda environment..."
sudo -u "$BOT_USER" bash -c "
    export PATH=\"$CONDA_INSTALL_DIR/bin:\$PATH\"
    cd \"$INSTALL_DIR\"
    
    # Initialize conda for the user
    $CONDA_INSTALL_DIR/bin/conda init bash
    source ~/.bashrc
    
    # Create environment if it doesn't exist
    if ! conda env list | grep -q \"$ENV_NAME\"; then
        conda env create -f environment.yml
        echo 'Conda environment created successfully'
    else
        echo 'Conda environment already exists, updating...'
        conda env update -f environment.yml --prune
    fi
"

# Copy bot files to installation directory
log "Copying bot files..."
cp -r . "$INSTALL_DIR/"
chown -R "$BOT_USER:$BOT_GROUP" "$INSTALL_DIR"

# Create .env file if it doesn't exist
if [ ! -f "$INSTALL_DIR/.env" ]; then
    log "Creating .env file from template..."
    cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"
    chown "$BOT_USER:$BOT_GROUP" "$INSTALL_DIR/.env"
    warn "Please edit $INSTALL_DIR/.env with your Discord token and other settings"
else
    warn ".env file already exists"
fi

# Initialize database
log "Initializing database..."
sudo -u "$BOT_USER" bash -c "
    export PATH=\"$CONDA_INSTALL_DIR/envs/$ENV_NAME/bin:\$PATH\"
    cd \"$INSTALL_DIR\"
    source \"$CONDA_INSTALL_DIR/etc/profile.d/conda.sh\"
    conda activate \"$ENV_NAME\"
    
    # Create logs directory
    mkdir -p logs
    
    # Initialize database with Alembic
    if [ ! -f alembic/versions/*.py ]; then
        echo 'Creating initial migration...'
        alembic revision --autogenerate -m 'Initial migration'
    fi
    
    # Run migrations
    alembic upgrade head
    
    echo 'Database initialized successfully'
"

# Install systemd service
log "Installing systemd service..."
cp "$INSTALL_DIR/systemd/habit-bot.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable habit-bot.service

# Create startup script for easier management
log "Creating management scripts..."
cat > "$INSTALL_DIR/start.sh" << 'EOF'
#!/bin/bash
export PATH="/opt/miniconda3/envs/habit-bot/bin:$PATH"
cd /opt/discord-habit-bot
source /opt/miniconda3/etc/profile.d/conda.sh
conda activate habit-bot
python bot.py
EOF

cat > "$INSTALL_DIR/manage.sh" << 'EOF'
#!/bin/bash
# Discord Habit Bot Management Script

case "$1" in
    start)
        echo "Starting Discord Habit Bot..."
        systemctl start habit-bot
        ;;
    stop)
        echo "Stopping Discord Habit Bot..."
        systemctl stop habit-bot
        ;;
    restart)
        echo "Restarting Discord Habit Bot..."
        systemctl restart habit-bot
        ;;
    status)
        systemctl status habit-bot
        ;;
    logs)
        journalctl -u habit-bot -f
        ;;
    update)
        echo "Updating bot..."
        git pull
        systemctl restart habit-bot
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|update}"
        exit 1
        ;;
esac
EOF

chmod +x "$INSTALL_DIR/start.sh"
chmod +x "$INSTALL_DIR/manage.sh"
chown "$BOT_USER:$BOT_GROUP" "$INSTALL_DIR/start.sh"
chown "$BOT_USER:$BOT_GROUP" "$INSTALL_DIR/manage.sh"

# Create some default habits
log "Creating default habits..."
sudo -u "$BOT_USER" bash -c "
    export PATH=\"$CONDA_INSTALL_DIR/envs/$ENV_NAME/bin:\$PATH\"
    cd \"$INSTALL_DIR\"
    source \"$CONDA_INSTALL_DIR/etc/profile.d/conda.sh\"
    conda activate \"$ENV_NAME\"
    
    python -c \"
import asyncio
from database import initialize_database
from services.habit_service import HabitService
from database import db_manager

async def create_defaults():
    await initialize_database()
    habit_service = HabitService(db_manager)
    
    # Create some default habits
    defaults = [
        ('Exercise', 'Daily physical activity', 15, 'fitness'),
        ('Meditation', 'Mindfulness practice', 12, 'wellness'),
        ('Reading', 'Read for learning', 10, 'learning'),
        ('Water Intake', 'Stay hydrated', 5, 'wellness'),
        ('Sleep Early', 'Good sleep hygiene', 10, 'wellness'),
    ]
    
    for name, desc, xp, category in defaults:
        try:
            await habit_service.create_habit(name, desc, xp, category)
            print(f'Created habit: {name}')
        except Exception as e:
            print(f'Habit {name} may already exist: {e}')

asyncio.run(create_defaults())
\"
"

success "Discord Habit Bot setup completed!"

echo ""
echo "============================================="
echo "🎉 SETUP COMPLETE!"
echo "============================================="
echo ""
echo "Next steps:"
echo "1. Edit the configuration file:"
echo "   sudo nano $INSTALL_DIR/.env"
echo ""
echo "2. Add your Discord bot token and other settings"
echo ""
echo "3. Start the bot:"
echo "   sudo systemctl start habit-bot"
echo ""
echo "4. Check status:"
echo "   sudo systemctl status habit-bot"
echo ""
echo "5. View logs:"
echo "   sudo journalctl -u habit-bot -f"
echo ""
echo "Management commands:"
echo "   $INSTALL_DIR/manage.sh {start|stop|restart|status|logs|update}"
echo ""
echo "The bot will automatically start on system boot."
echo "============================================="