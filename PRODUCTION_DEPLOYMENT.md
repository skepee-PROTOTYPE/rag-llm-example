# Production Deployment Guide

## Repository Security Status

✅ **Security Checklist:**
- [x] No `.env` files committed
- [x] All secrets use environment variables
- [x] `.gitignore` configured for secrets and cache
- [x] `.env.example` provided
- [x] Security policy documented (SECURITY.md)
- [ ] GitHub secret scanning enabled (manual step required)
- [ ] Dependabot enabled (manual step required)

### Enable GitHub Security Features

1. Go to repository Settings → Security → Code security and analysis
2. Enable:
   - **Secret scanning** - detects accidentally committed secrets
   - **Push protection** - blocks secret commits
   - **Dependabot alerts** - security vulnerability notifications
   - **Dependabot security updates** - automatic security patches

## Deployment Options

### Option 1: Google Cloud Run (Recommended for Firebase users)

**Prerequisites:**
- Google Cloud account
- `gcloud` CLI installed
- Docker installed locally

**Step 1: Setup GCP Project**
```powershell
# Login
gcloud auth login

# Create/select project
gcloud projects create knowledge-rag-prod
gcloud config set project knowledge-rag-prod

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable secretmanager.googleapis.com
```

**Step 2: Store Secrets**
```powershell
# Store GitHub token in Secret Manager
echo -n "your_actual_token_here" | gcloud secrets create github-token --data-file=-

# Grant Cloud Run access to secret
gcloud secrets add-iam-policy-binding github-token `
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" `
  --role="roles/secretmanager.secretAccessor"
```

**Step 3: Build and Deploy**
```powershell
# Build container
gcloud builds submit --tag gcr.io/PROJECT_ID/knowledge-rag

# Deploy to Cloud Run
gcloud run deploy knowledge-rag `
  --image gcr.io/PROJECT_ID/knowledge-rag `
  --platform managed `
  --region us-central1 `
  --allow-unauthenticated `
  --set-secrets GITHUB_TOKEN=github-token:latest `
  --memory 2Gi `
  --cpu 2 `
  --timeout 300 `
  --concurrency 80 `
  --min-instances 0 `
  --max-instances 10
```

**Step 4: Get Service URL**
```powershell
gcloud run services describe knowledge-rag `
  --region us-central1 `
  --format 'value(status.url)'
```

### Option 2: Azure Web App

**Prerequisites:**
- Azure account
- Azure CLI installed

**Step 1: Setup Azure**
```powershell
# Login
az login

# Create resource group
az group create --name knowledge-rag-rg --location eastus

# Create container registry
az acr create --resource-group knowledge-rag-rg `
  --name knowledgeragacr --sku Basic

# Login to registry
az acr login --name knowledgeragacr
```

**Step 2: Build and Push**
```powershell
# Build and push container
az acr build --registry knowledgeragacr `
  --image knowledge-rag:latest .
```

**Step 3: Create Web App**
```powershell
# Create App Service plan
az appservice plan create --name knowledge-rag-plan `
  --resource-group knowledge-rag-rg `
  --is-linux --sku B1

# Create web app
az webapp create --resource-group knowledge-rag-rg `
  --plan knowledge-rag-plan `
  --name knowledge-rag-app `
  --deployment-container-image-name knowledgeragacr.azurecr.io/knowledge-rag:latest

# Configure environment variables
az webapp config appsettings set `
  --resource-group knowledge-rag-rg `
  --name knowledge-rag-app `
  --settings GITHUB_TOKEN=your_token_here FLASK_ENV=production
```

### Option 3: Heroku

**Prerequisites:**
- Heroku account
- Heroku CLI installed

**Step 1: Create App**
```powershell
# Login
heroku login

# Create app
heroku create knowledge-rag-prod

# Add container stack
heroku stack:set container -a knowledge-rag-prod
```

**Step 2: Set Secrets**
```powershell
heroku config:set GITHUB_TOKEN=your_token_here -a knowledge-rag-prod
heroku config:set FLASK_ENV=production -a knowledge-rag-prod
```

**Step 3: Deploy**
```powershell
# Push to Heroku
git push heroku main

# Open app
heroku open -a knowledge-rag-prod
```

## GitHub Actions CI/CD

The repository includes two GitHub Actions workflows:

### CI Workflow (`.github/workflows/ci.yml`)
- Runs on every push and pull request
- Tests code formatting, linting, security
- Builds Docker image

### Deployment Workflow (`.github/workflows/deploy.yml`)
- Deploys to Google Cloud Run on push to main
- Requires GitHub secrets configuration

**Required GitHub Secrets:**
1. Go to Repository → Settings → Secrets and variables → Actions
2. Add these secrets:
   - `GCP_PROJECT_ID` - Your GCP project ID
   - `GCP_WORKLOAD_IDENTITY_PROVIDER` - Workload identity provider
   - `GCP_SERVICE_ACCOUNT` - Service account email

**Setup Workload Identity Federation:**
```powershell
# Create service account
gcloud iam service-accounts create github-actions `
  --display-name="GitHub Actions"

# Grant permissions
gcloud projects add-iam-policy-binding PROJECT_ID `
  --member="serviceAccount:github-actions@PROJECT_ID.iam.gserviceaccount.com" `
  --role="roles/run.admin"

# Create workload identity pool
gcloud iam workload-identity-pools create github `
  --location="global" `
  --display-name="GitHub Actions"

# Create provider
gcloud iam workload-identity-pools providers create-oidc github `
  --location="global" `
  --workload-identity-pool="github" `
  --issuer-uri="https://token.actions.githubusercontent.com" `
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository"

# Bind service account
gcloud iam service-accounts add-iam-policy-binding `
  github-actions@PROJECT_ID.iam.gserviceaccount.com `
  --role="roles/iam.workloadIdentityUser" `
  --member="principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github/attribute.repository/OWNER/REPO"
```

## Production Configuration

### Environment Variables

Set these in your deployment platform:

```bash
# Required
GITHUB_TOKEN=<your_github_token>

# Production settings
FLASK_ENV=production
LOG_LEVEL=INFO
CACHE_DIR=/app/cache

# Optional performance tuning
MAX_WORKERS=4
REQUEST_TIMEOUT=30
```

### Dockerfile

The included `Dockerfile` is production-ready:
- Uses Python 3.13 slim image
- Runs as non-root user
- Includes Gunicorn for production WSGI
- Health check configured
- Port 8080 exposed

### Security Hardening

1. **Rate Limiting**: The `rate_limiter.py` provides in-memory rate limiting. For production with multiple instances, use Redis:

```powershell
pip install Flask-Limiter redis
```

Update `app.py`:
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    storage_uri="redis://localhost:6379"
)

@app.route('/api/ask')
@limiter.limit("10 per minute")
def ask_question():
    ...
```

2. **HTTPS**: All cloud platforms provide automatic HTTPS. For custom domains:
   - Cloud Run: Add custom domain in console
   - Azure: Configure custom domain and SSL
   - Heroku: Use ACM for automatic certificates

3. **CORS**: Add Flask-CORS for API access:
```powershell
pip install flask-cors
```

```python
from flask_cors import CORS
CORS(app, origins=["https://yourdomain.com"])
```

## Persistent Storage

ChromaDB stores embeddings locally. For production:

### Option A: Mounted Volume (Cloud Run)
```powershell
# Create a Cloud Storage bucket
gsutil mb gs://knowledge-rag-cache

# Mount in Cloud Run (available in preview)
gcloud run deploy knowledge-rag `
  --add-volume name=cache,type=cloud-storage,bucket=knowledge-rag-cache `
  --add-volume-mount volume=cache,mount-path=/app/cache
```

### Option B: Managed Vector Database
Consider migrating to a managed vector database:
- **Pinecone** - serverless vector database
- **Chroma Cloud** - hosted ChromaDB
- **Azure AI Search** - Azure's vector search
- **Weaviate Cloud** - open-source vector database

## Monitoring and Logging

### Cloud Run
```powershell
# View logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=knowledge-rag" --limit 50

# Set up alerts
gcloud alpha monitoring policies create `
  --notification-channels=CHANNEL_ID `
  --display-name="High Error Rate" `
  --condition-display-name="Error rate > 5%" `
  --condition-threshold-value=0.05
```

### Azure
```powershell
# View logs
az webapp log tail --name knowledge-rag-app --resource-group knowledge-rag-rg

# Enable Application Insights
az monitor app-insights component create `
  --app knowledge-rag-insights `
  --location eastus `
  --resource-group knowledge-rag-rg
```

## Testing Production Deployment

```powershell
# Test endpoint
curl -X POST https://your-app-url/api/ask `
  -H "Content-Type: application/json" `
  -d '{"question":"What is machine learning?"}'

# Check stats
curl https://your-app-url/api/stats

# Load test (optional)
ab -n 100 -c 10 -p question.json -T application/json https://your-app-url/api/ask
```

## Rollback Strategy

### Cloud Run
```powershell
# List revisions
gcloud run revisions list --service knowledge-rag --region us-central1

# Rollback to previous revision
gcloud run services update-traffic knowledge-rag `
  --to-revisions REVISION_NAME=100 `
  --region us-central1
```

### Azure
```powershell
# List deployments
az webapp deployment list --name knowledge-rag-app --resource-group knowledge-rag-rg

# Swap slots (if using deployment slots)
az webapp deployment slot swap `
  --name knowledge-rag-app `
  --resource-group knowledge-rag-rg `
  --slot staging
```

## Cost Optimization

### Cloud Run
- **Min instances**: Set to 0 for dev/staging
- **Max instances**: Limit based on budget
- **Memory**: Start with 512MB, increase if needed
- **CPU**: Use 1 CPU for light workloads

### Azure
- **App Service Plan**: Start with B1 (Basic), upgrade as needed
- **Scaling**: Enable auto-scaling based on CPU/memory

## Backup and Disaster Recovery

```powershell
# Backup ChromaDB cache (Cloud Run example)
gsutil -m rsync -r /app/cache gs://knowledge-rag-backups/$(date +%Y%m%d)

# Scheduled backups (Cloud Scheduler)
gcloud scheduler jobs create http backup-chroma `
  --schedule="0 2 * * *" `
  --uri="https://your-app-url/admin/backup" `
  --http-method=POST
```

## Next Steps

1. ✅ Enable GitHub security features (manual)
2. ✅ Choose deployment platform
3. ✅ Configure secrets in deployment platform
4. ✅ Deploy using one of the methods above
5. ✅ Test production deployment
6. ✅ Set up monitoring and alerts
7. ✅ Configure backups
8. ✅ Document custom domain setup (if needed)
9. ✅ Plan scaling strategy

## Support

For issues or questions:
- Check SECURITY.md for security policies
- Review logs in your deployment platform
- Check GitHub Actions for CI/CD issues
