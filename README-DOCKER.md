
# 🎵 YouTube Music Streaming - Docker Setup

## Quick Start (3 Steps!)

### 1. Install Docker
- Download Docker Desktop: https://www.docker.com/products/docker-desktop

### 2. Start the Application
```bash
# Linux/Mac
chmod +x start.sh
./start.sh

# Windows
docker-compose up -d
```

### 3. Open Your Browser
- Application: http://localhost:8000
- API Docs: http://localhost:8000/docs

That's it! 🎉

---

## Manual Commands

### Start Application
```bash
docker-compose up -d
```

### View Logs
```bash
docker-compose logs -f
```

### Stop Application
```bash
docker-compose down
```

### Restart Application
```bash
docker-compose restart
```

### Build from Scratch
```bash
docker-compose build --no-cache
docker-compose up -d
```

---

## Production Deployment

### 1. Create .env file
```bash
cp .env.example .env
nano .env  # Edit with your settings
```

**Important:** Change these in .env:
- `SECRET_KEY` - Use a long random string
- `REDIS_PASSWORD` - Set a strong password
- `DEBUG=False`

### 2. Deploy
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### 3. Setup Domain (Optional)
Use a reverse proxy like Caddy or Traefik for HTTPS.

Simple Caddy setup:
```bash
# Install Caddy
sudo apt install caddy

# Create Caddyfile
echo "yourdomain.com {
    reverse_proxy localhost:8000
}" > Caddyfile

# Start Caddy
sudo caddy start
```

---

## Troubleshooting

### Port Already in Use
```bash
# Change port in docker-compose.yml
ports:
  - "8080:8000"  # Use 8080 instead of 8000
```

### Can't Access Application
```bash
# Check if containers are running
docker-compose ps

# Check logs
docker-compose logs -f app
```

### Reset Everything
```bash
docker-compose down -v
docker-compose up -d
```

---

## File Structure
```
your-project/
├── app/                    # Backend code
├── frontend/              
│   └── index.html         # Frontend (automatically served)
├── docker-compose.yml     # Development config
├── docker-compose.prod.yml # Production config
├── Dockerfile             # Docker build instructions
├── requirements.txt       # Python dependencies
├── .env                   # Your configuration
└── start.sh              # Quick start script
```

---

## Data Storage

All data is stored in Docker volumes:
- Database: `app-data` volume
- Cache: `redis-data` volume
- Logs: `./logs` folder

### Backup Your Data
```bash
# Backup database
docker-compose exec app cp /app/data/music_app.db /app/logs/backup.db

# Copy to your computer
docker cp ytmusic-app:/app/logs/backup.db ./backup.db
```

---

## Support

- View logs: `docker-compose logs -f`
- Access container: `docker-compose exec app bash`
- Check health: `curl http://localhost:8000/health`