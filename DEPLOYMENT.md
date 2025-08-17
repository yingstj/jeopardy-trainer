# 🚀 Jay's Jeopardy Trainer - Deployment Guide

This comprehensive guide covers all deployment options for Jay's Jeopardy Trainer, from quick local setup to production cloud deployments.

## 📋 Quick Summary

| Platform | Difficulty | Cost | Best For |
|----------|------------|------|----------|
| [Local Development](#local-development) | Easy | Free | Testing & development |
| [Streamlit Cloud](#streamlit-cloud-recommended) | Easy | Free | Public apps, sharing |
| [Railway](#railway) | Easy | Free tier | Quick cloud deployment |
| [Render](#render) | Easy | Free tier | Alternative cloud option |
| [Heroku](#heroku) | Medium | Free tier | Traditional PaaS |
| [Docker](#docker-deployment) | Medium | Varies | Containerized deployment |
| [Self-hosted](#self-hosted-vps) | Hard | Varies | Full control |

---

## 🏠 Local Development

Perfect for testing and development.

### Option 1: One-Click Setup (Recommended)
```bash
# Clone the repository
git clone https://github.com/yingstj/jeopardy-trainer.git
cd jeopardy-trainer

# Run the setup script
./run_local.sh
```

### Option 2: Manual Setup
```bash
# Clone the repository
git clone https://github.com/yingstj/jeopardy-trainer.git
cd jeopardy-trainer

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

### Option 3: Setup Wizard
```bash
python3 setup_local.py
```

**Access:** http://localhost:8501

---

## ☁️ Streamlit Cloud (Recommended)

**Best for:** Public applications, easy sharing, zero configuration

### Prerequisites
- GitHub account
- Public GitHub repository

### Steps

1. **Prepare Repository**
   ```bash
   # Fork or create repository
   git clone https://github.com/yourusername/jeopardy-trainer.git
   cd jeopardy-trainer
   git push origin main
   ```

2. **Deploy to Streamlit Cloud**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Sign in with GitHub
   - Click "New app"
   - Select your repository
   - Main file path: `app.py`
   - Click "Deploy!"

3. **Configure Environment Variables** (Optional)
   - Go to app settings → "Secrets"
   - Add your Cloudflare R2 credentials:
   ```toml
   R2_ENDPOINT_URL = "your-r2-endpoint"
   R2_ACCESS_KEY = "your-access-key"
   R2_SECRET_KEY = "your-secret-key"
   R2_BUCKET_NAME = "jeopardy-dataset"
   R2_FILE_KEY = "all_jeopardy_clues.csv"
   ```

**Pros:**
- ✅ Free hosting
- ✅ Automatic deployments from GitHub
- ✅ Built-in SSL/HTTPS
- ✅ Easy domain management

**Cons:**
- ❌ Limited to public repositories (unless paid)
- ❌ Resource limitations
- ❌ Streamlit-specific platform

---

## 🚂 Railway

**Best for:** Quick cloud deployment with minimal configuration

### Steps

1. **Install Railway CLI**
   ```bash
   npm install -g @railway/cli
   # or
   curl -fsSL https://railway.app/install.sh | sh
   ```

2. **Deploy**
   ```bash
   cd jeopardy-trainer
   railway login
   railway init
   railway up
   ```

3. **Configure Environment Variables**
   ```bash
   railway variables set R2_ENDPOINT_URL=your-endpoint
   railway variables set R2_ACCESS_KEY=your-key
   railway variables set R2_SECRET_KEY=your-secret
   railway variables set R2_BUCKET_NAME=jeopardy-dataset
   railway variables set R2_FILE_KEY=all_jeopardy_clues.csv
   ```

4. **Create `railway.toml`**
   ```toml
   [build]
   builder = "nixpacks"

   [deploy]
   startCommand = "streamlit run app.py --server.port $PORT --server.address 0.0.0.0"
   ```

**Pros:**
- ✅ $5/month free tier
- ✅ Git-based deployments
- ✅ Easy environment variables
- ✅ Custom domains

---

## 🎨 Render

**Best for:** Alternative cloud platform with good free tier

### Steps

1. **Create `render.yaml`**
   ```yaml
   services:
     - type: web
       name: jeopardy-trainer
       env: python
       buildCommand: pip install -r requirements.txt
       startCommand: streamlit run app.py --server.port $PORT --server.address 0.0.0.0
       envVars:
         - key: R2_ENDPOINT_URL
           value: your-endpoint
         - key: R2_ACCESS_KEY
           value: your-key
         - key: R2_SECRET_KEY
           value: your-secret
         - key: R2_BUCKET_NAME
           value: jeopardy-dataset
         - key: R2_FILE_KEY
           value: all_jeopardy_clues.csv
   ```

2. **Deploy**
   - Go to [render.com](https://render.com)
   - Connect GitHub repository
   - Select "Web Service"
   - Deploy with settings from `render.yaml`

**Pros:**
- ✅ Free tier available
- ✅ Auto-deployments from Git
- ✅ Easy SSL certificates
- ✅ Good performance

---

## 🏗️ Heroku

**Best for:** Traditional PaaS deployment

### Prerequisites
- Heroku account
- Heroku CLI

### Steps

1. **Create `Procfile`**
   ```
   web: streamlit run app.py --server.port $PORT --server.address 0.0.0.0
   ```

2. **Create `runtime.txt`**
   ```
   python-3.11.0
   ```

3. **Deploy**
   ```bash
   heroku create your-jeopardy-trainer
   heroku config:set R2_ENDPOINT_URL=your-endpoint
   heroku config:set R2_ACCESS_KEY=your-key
   heroku config:set R2_SECRET_KEY=your-secret
   heroku config:set R2_BUCKET_NAME=jeopardy-dataset
   heroku config:set R2_FILE_KEY=all_jeopardy_clues.csv
   git push heroku main
   ```

**Note:** Heroku removed their free tier. Starts at $5/month.

---

## 🐳 Docker Deployment

**Best for:** Containerized deployments, self-hosting

### Create `Dockerfile`
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### Create `docker-compose.yml`
```yaml
version: '3.8'
services:
  jeopardy-trainer:
    build: .
    ports:
      - "8501:8501"
    environment:
      - R2_ENDPOINT_URL=${R2_ENDPOINT_URL}
      - R2_ACCESS_KEY=${R2_ACCESS_KEY}
      - R2_SECRET_KEY=${R2_SECRET_KEY}
      - R2_BUCKET_NAME=${R2_BUCKET_NAME:-jeopardy-dataset}
      - R2_FILE_KEY=${R2_FILE_KEY:-all_jeopardy_clues.csv}
```

### Deploy
```bash
# Build and run
docker-compose up --build

# Or with Docker only
docker build -t jeopardy-trainer .
docker run -p 8501:8501 \
  -e R2_ENDPOINT_URL=your-endpoint \
  -e R2_ACCESS_KEY=your-key \
  -e R2_SECRET_KEY=your-secret \
  jeopardy-trainer
```

---

## 🖥️ Self-hosted VPS

**Best for:** Full control, custom domains, high performance

### Requirements
- VPS with Ubuntu/Debian
- Domain name (optional)
- Basic Linux knowledge

### Steps

1. **Setup Server**
   ```bash
   # Update system
   sudo apt update && sudo apt upgrade -y

   # Install Python and dependencies
   sudo apt install python3 python3-pip python3-venv nginx -y

   # Clone repository
   git clone https://github.com/yourusername/jeopardy-trainer.git
   cd jeopardy-trainer

   # Setup Python environment
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Create Systemd Service**
   ```bash
   sudo nano /etc/systemd/system/jeopardy-trainer.service
   ```
   
   ```ini
   [Unit]
   Description=Jeopardy Trainer Streamlit App
   After=network.target

   [Service]
   User=ubuntu
   WorkingDirectory=/home/ubuntu/jeopardy-trainer
   Environment=PATH=/home/ubuntu/jeopardy-trainer/venv/bin
   ExecStart=/home/ubuntu/jeopardy-trainer/venv/bin/streamlit run app.py --server.port 8501
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

3. **Configure Nginx**
   ```bash
   sudo nano /etc/nginx/sites-available/jeopardy-trainer
   ```
   
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://localhost:8501;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
           proxy_set_header Host $host;
           proxy_cache_bypass $http_upgrade;
       }
   }
   ```

4. **Enable and Start Services**
   ```bash
   sudo ln -s /etc/nginx/sites-available/jeopardy-trainer /etc/nginx/sites-enabled
   sudo systemctl enable jeopardy-trainer
   sudo systemctl start jeopardy-trainer
   sudo systemctl reload nginx
   ```

5. **Setup SSL (Optional)**
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d your-domain.com
   ```

---

## 🔧 Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `R2_ENDPOINT_URL` | No | Hardcoded | Cloudflare R2 endpoint |
| `R2_ACCESS_KEY` | No | Hardcoded | R2 access key |
| `R2_SECRET_KEY` | No | Hardcoded | R2 secret key |
| `R2_BUCKET_NAME` | No | `jeopardy-dataset` | Bucket name |
| `R2_FILE_KEY` | No | `all_jeopardy_clues.csv` | Dataset filename |

### Streamlit Configuration

Create `.streamlit/config.toml`:
```toml
[server]
port = 8501
address = "0.0.0.0"
enableCORS = true

[theme]
primaryColor = "#060CE9"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
font = "sans serif"
```

---

## 🔍 Troubleshooting

### Common Issues

**1. Port Already in Use**
```bash
# Change port
streamlit run app.py --server.port 8502
```

**2. Module Not Found**
```bash
# Reinstall dependencies
pip install -r requirements.txt
```

**3. Data Loading Fails**
- Check environment variables
- Verify R2 credentials
- Ensure network connectivity

**4. Memory Issues**
```bash
# Monitor usage
htop
# Increase server memory if needed
```

### Performance Optimization

**1. Enable Caching**
- Data loading is already cached with `@st.cache_data`
- Model loading cached with `@st.cache_resource`

**2. Optimize Docker**
```dockerfile
# Multi-stage build
FROM python:3.11-slim as builder
COPY requirements.txt .
RUN pip install --user -r requirements.txt

FROM python:3.11-slim
COPY --from=builder /root/.local /root/.local
COPY . .
```

**3. Use CDN for Static Assets**
- Host large datasets on CDN
- Use Cloudflare R2 for better performance

---

## 🔒 Security Considerations

### Production Checklist

- [ ] Use HTTPS/SSL
- [ ] Set strong environment variables
- [ ] Enable authentication if needed
- [ ] Regular security updates
- [ ] Monitor resource usage
- [ ] Backup user data
- [ ] Rate limiting (if needed)

### Authentication

The app includes optional authentication:
```python
# Enable authentication by uncommenting in app.py
from auth_manager import AuthManager
auth = AuthManager()
```

See `AUTH_SETUP.md` for detailed authentication configuration.

---

## 📊 Monitoring

### Health Checks

```bash
# Check app status
curl http://localhost:8501/_stcore/health

# Monitor logs
tail -f ~/.streamlit/logs/app.log
```

### Performance Monitoring

```bash
# Resource usage
docker stats
# or
htop
```

---

## 🤝 Support

If you encounter issues:

1. Check this guide
2. Review `SHARE_GUIDE.md`
3. Test authentication with `test_auth.py`
4. Reset with `./run_local.sh`
5. Create GitHub issue

---

## 📝 License

This deployment guide is part of Jay's Jeopardy Trainer project.