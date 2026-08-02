# Deployment Guide

Complete guide for deploying your Payment Gateway backend to production.

## Pre-Deployment Checklist

### 1. Code Review
- [ ] All tests passing
- [ ] No hardcoded credentials
- [ ] Error handling implemented
- [ ] Logging configured
- [ ] Rate limiting tested
- [ ] CORS properly configured

### 2. Security
- [ ] Environment variables set
- [ ] Secret keys rotated
- [ ] Database credentials secured
- [ ] HTTPS/SSL configured
- [ ] Webhook signatures verified
- [ ] Production Paystack keys obtained

### 3. Infrastructure
- [ ] PostgreSQL database provisioned
- [ ] Redis instance running
- [ ] Backup strategy in place
- [ ] Monitoring tools configured
- [ ] Log aggregation setup

## Deployment Options

### Option 1: Traditional VPS (DigitalOcean, Linode, AWS EC2)

#### Step 1: Provision Server
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install python3.13 python3-pip postgresql redis-server nginx -y
```

#### Step 2: Set Up Application
```bash
# Create application directory
sudo mkdir -p /var/www/payment-gateway
cd /var/www/payment-gateway

# Clone repository
git clone <your-repo-url> .

# Create virtual environment
python3.13 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### Step 3: Configure Environment
```bash
# Create .env file
sudo nano .env

# Add production variables
SECRET_KEY=<strong-random-secret>
FLASK_DEBUG=False
PAYSTACK_SECRET_KEY=sk_live_<your-live-key>
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=payment_user
POSTGRES_PASSWORD=<strong-password>
POSTGRES_DB=payment_gateway
```

#### Step 4: Set Up Database
```bash
# Create database user
sudo -u postgres psql
CREATE DATABASE payment_gateway;
CREATE USER payment_user WITH PASSWORD 'strong-password';
GRANT ALL PRIVILEGES ON DATABASE payment_gateway TO payment_user;
\q

# Run migrations (never use db.create_all in production)
source .venv/bin/activate
AUTO_CREATE_SCHEMA=false flask --app run:app db upgrade
```

#### Step 5: Configure Gunicorn
```bash
# Install gunicorn
pip install gunicorn

# Create systemd service
sudo nano /etc/systemd/system/payment-gateway.service
```

**Service file content:**
```ini
[Unit]
Description=Payment Gateway Application
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/var/www/payment-gateway
Environment="PATH=/var/www/payment-gateway/.venv/bin"
ExecStart=/var/www/payment-gateway/.venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 "src.app.main:app"
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl enable payment-gateway
sudo systemctl start payment-gateway
sudo systemctl status payment-gateway
```

#### Step 6: Configure Nginx
```bash
sudo nano /etc/nginx/sites-available/payment-gateway
```

**Nginx configuration:**
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/payment-gateway /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### Step 7: Set Up SSL with Let's Encrypt
```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx -y

# Obtain certificate
sudo certbot --nginx -d yourdomain.com

# Auto-renewal is configured automatically
```

### Option 2: Docker Deployment

#### Create Dockerfile
```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 5000

# Run application
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "src.app.main:app"]
```

#### Create docker-compose.yml
```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - SECRET_KEY=${SECRET_KEY}
      - FLASK_DEBUG=False
      - PAYSTACK_SECRET_KEY=${PAYSTACK_SECRET_KEY}
      - POSTGRES_HOST=db
      - POSTGRES_PORT=5432
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=payment_gateway
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
    restart: always

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=payment_gateway
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: always

  redis:
    image: redis:7
    restart: always

volumes:
  postgres_data:
```

#### Deploy with Docker
```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f web

# Stop
docker-compose down
```

### Option 3: Platform as a Service (Render, Heroku, Railway)

#### For Render.com

1. **Create `render.yaml`:**
```yaml
services:
  - type: web
    name: payment-gateway
    env: python
    buildCommand: npm ci && npm run build:css && uv sync --frozen
    startCommand: uv run gunicorn -w 2 --timeout 120 -b 0.0.0.0:$PORT run:app
    envVars:
      - key: SECRET_KEY
        generateValue: true
      - key: FLASK_DEBUG
        value: False
      - key: APP_ENV
        value: production
      - key: AUTO_CREATE_SCHEMA
        value: "false"
      - key: TRUST_PROXY_HEADERS
        value: "true"
      - key: ALLOWED_ORIGINS
        sync: false
      - key: RATELIMIT_STORAGE_URI
        sync: false
      - key: PAYSTACK_SECRET_KEY
        sync: false
      - key: POSTGRES_HOST
        fromDatabase:
          name: payment-gateway-db
          property: host
      - key: POSTGRES_PORT
        fromDatabase:
          name: payment-gateway-db
          property: port
      - key: POSTGRES_USER
        fromDatabase:
          name: payment-gateway-db
          property: user
      - key: POSTGRES_PASSWORD
        fromDatabase:
          name: payment-gateway-db
          property: password
      - key: POSTGRES_DB
        fromDatabase:
          name: payment-gateway-db
          property: database
      - key: REDIS_URL
        fromService:
          type: redis
          name: payment-gateway-redis
          property: connectionString

databases:
  - name: payment-gateway-db
    databaseName: payment_gateway
    user: payment_user

services:
  - type: redis
    name: payment-gateway-redis
    plan: starter
```

2. **Connect to GitHub and deploy**
3. **Add environment variables in Render dashboard**

#### For Heroku

```bash
# Install Heroku CLI
# Login
heroku login

# Create app
heroku create payment-gateway-app

# Add PostgreSQL
heroku addons:create heroku-postgresql:mini

# Add Redis
heroku addons:create heroku-redis:mini

# Set environment variables
heroku config:set SECRET_KEY=<your-secret>
heroku config:set FLASK_DEBUG=False
heroku config:set PAYSTACK_SECRET_KEY=sk_live_<your-key>

# Create Procfile
echo "web: gunicorn -w 4 src.app.main:app" > Procfile

# Deploy
git push heroku main

# Run migrations
heroku run python run.py
```

## Post-Deployment

### 1. Verify Deployment
```bash
# Test health endpoint
curl https://yourdomain.com/health

# Test authentication
curl -X POST https://yourdomain.com/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123","name":"Test User"}'
```

### 2. Configure Paystack Webhooks
1. Go to Paystack Dashboard → Settings → Webhooks
2. Add webhook URL: `https://yourdomain.com/api/v1/paystack/webhook`
3. Select events to listen to
4. Save configuration

### 3. Set Up Monitoring

#### Application Monitoring (Sentry)
```bash
pip install sentry-sdk[flask]
```

Add to `main.py`:
```python
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

sentry_sdk.init(
    dsn="your-sentry-dsn",
    integrations=[FlaskIntegration()],
    traces_sample_rate=1.0
)
```

#### Uptime Monitoring
- UptimeRobot (free): https://uptimerobot.com
- Pingdom: https://www.pingdom.com
- Better Uptime: https://betteruptime.com

### 4. Set Up Logging

#### CloudWatch (AWS)
```bash
pip install watchtower
```

#### Papertrail
```bash
# Configure rsyslog to forward logs
```

### 5. Database Backups

#### Automated PostgreSQL Backups
```bash
# Create backup script
sudo nano /usr/local/bin/backup-db.sh
```

**Backup script:**
```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/var/backups/postgresql"
mkdir -p $BACKUP_DIR

pg_dump -U payment_user payment_gateway | gzip > $BACKUP_DIR/payment_gateway_$DATE.sql.gz

# Keep only last 30 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
```

```bash
# Make executable
sudo chmod +x /usr/local/bin/backup-db.sh

# Add to crontab (daily at 2 AM)
sudo crontab -e
0 2 * * * /usr/local/bin/backup-db.sh
```

## Monitoring & Maintenance

### Health Checks
- Monitor `/health` endpoint
- Set up alerts for downtime
- Track response times

### Database Maintenance
```bash
# Vacuum database (weekly)
psql -U payment_user -d payment_gateway -c "VACUUM ANALYZE;"

# Check database size
psql -U payment_user -d payment_gateway -c "SELECT pg_size_pretty(pg_database_size('payment_gateway'));"
```

### Redis Maintenance
```bash
# Monitor Redis memory
redis-cli info memory

# Check connected clients
redis-cli client list
```

### Log Rotation
```bash
# Configure logrotate
sudo nano /etc/logrotate.d/payment-gateway

/var/log/payment-gateway/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
}
```

## Scaling

### Horizontal Scaling
- Add more gunicorn workers
- Deploy multiple instances behind load balancer
- Use managed database service (AWS RDS, etc.)

### Vertical Scaling
- Increase server resources
- Optimize database queries
- Implement caching with Redis

## Rollback Strategy

### Quick Rollback
```bash
# Using systemd
sudo systemctl stop payment-gateway
cd /var/www/payment-gateway
git checkout <previous-commit>
sudo systemctl start payment-gateway

# Using Docker
docker-compose down
docker-compose up -d --build
```

### Database Rollback
```bash
# Restore from backup
gunzip < /var/backups/postgresql/payment_gateway_YYYYMMDD.sql.gz | \
  psql -U payment_user payment_gateway
```

## Troubleshooting

### Application Won't Start
```bash
# Check logs
sudo journalctl -u payment-gateway -n 50

# Check gunicorn
ps aux | grep gunicorn

# Test configuration
source .venv/bin/activate
python run.py
```

### Database Connection Issues
```bash
# Test connection
psql -U payment_user -h localhost -d payment_gateway

# Check PostgreSQL status
sudo systemctl status postgresql
```

### High Memory Usage
```bash
# Check memory
free -h

# Monitor processes
top

# Reduce gunicorn workers if needed
```

## Security Hardening

### Firewall
```bash
# Enable UFW
sudo ufw enable
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

### Fail2ban
```bash
# Install
sudo apt install fail2ban

# Configure for nginx
sudo nano /etc/fail2ban/jail.local
```

### Regular Updates
```bash
# System updates
sudo apt update && sudo apt upgrade -y

# Python packages
pip list --outdated
```

## Support & Resources

- **Documentation**: See README.md
- **API Reference**: See api_collection.json
- **Paystack Support**: support@paystack.com
- **Community**: GitHub Issues

## Maintenance Windows

Schedule regular maintenance:
- Database optimization: Weekly
- Security updates: As needed
- Dependency updates: Monthly
- Backup verification: Weekly

---

**Remember:** Always test in a staging environment before deploying to production!
