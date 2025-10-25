# Firebase + Cloud Run Deployment Guide

Complete guide to deploy Knowledge RAG to Firebase Hosting + Google Cloud Run.

## Architecture

```
User Browser
    ↓
Firebase Hosting (static UI + CDN)
    ↓
Google Cloud Run (Flask API backend)
    ↓
ChromaDB (persistent storage)
    ↓
GitHub Models API (OpenAI-compatible)
```

## Prerequisites

1. **Google Cloud Project**
   ```powershell
   gcloud projects create knowledge-rag-prod
   gcloud config set project knowledge-rag-prod
   ```

2. **Install Tools**
   - [gcloud CLI](https://cloud.google.com/sdk/docs/install)
   - [Firebase CLI](https://firebase.google.com/docs/cli)
   - Docker Desktop

3. **Enable APIs**
   ```powershell
   gcloud services enable run.googleapis.com
   gcloud services enable containerregistry.googleapis.com
   gcloud services enable secretmanager.googleapis.com
   gcloud services enable cloudbuild.googleapis.com
   ```

## Step 1: Store Secrets in Secret Manager

```powershell
# Store GitHub token
echo -n "ghp_your_actual_github_token" | gcloud secrets create github-token --data-file=-

# Verify
gcloud secrets versions list github-token

# Grant Cloud Run access
$PROJECT_NUMBER = gcloud projects describe knowledge-rag-prod --format="value(projectNumber)"
gcloud secrets add-iam-policy-binding github-token `
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" `
  --role="roles/secretmanager.secretAccessor"
```

## Step 2: Build and Deploy Backend to Cloud Run

### Option A: Using Cloud Build (Recommended)

```powershell
# Build container in cloud
gcloud builds submit --tag gcr.io/knowledge-rag-prod/knowledge-rag

# Deploy to Cloud Run
gcloud run deploy knowledge-rag `
  --image gcr.io/knowledge-rag-prod/knowledge-rag `
  --platform managed `
  --region us-central1 `
  --allow-unauthenticated `
  --set-secrets GITHUB_TOKEN=github-token:latest `
  --set-env-vars FLASK_ENV=production,LOG_LEVEL=INFO,CACHE_DIR=/app/cache `
  --memory 2Gi `
  --cpu 2 `
  --timeout 300 `
  --concurrency 80 `
  --min-instances 0 `
  --max-instances 10

# Get service URL
$SERVICE_URL = gcloud run services describe knowledge-rag --region us-central1 --format 'value(status.url)'
echo "Service URL: $SERVICE_URL"
```

### Option B: Build Locally and Push

```powershell
# Configure Docker for GCR
gcloud auth configure-docker

# Build locally
docker build -t gcr.io/knowledge-rag-prod/knowledge-rag:latest .

# Push to registry
docker push gcr.io/knowledge-rag-prod/knowledge-rag:latest

# Deploy
gcloud run deploy knowledge-rag `
  --image gcr.io/knowledge-rag-prod/knowledge-rag:latest `
  --platform managed `
  --region us-central1 `
  --allow-unauthenticated `
  --set-secrets GITHUB_TOKEN=github-token:latest `
  --memory 2Gi `
  --cpu 2
```

## Step 3: Test Cloud Run Backend

```powershell
# Get service URL
$SERVICE_URL = gcloud run services describe knowledge-rag --region us-central1 --format 'value(status.url)'

# Test stats endpoint
curl "$SERVICE_URL/api/stats"

# Test ask endpoint
curl -X POST "$SERVICE_URL/api/ask" `
  -H "Content-Type: application/json" `
  -d '{"question":"What is machine learning?"}'
```

## Step 4: Configure Firebase Hosting

### Initialize Firebase

```powershell
# Login to Firebase
firebase login

# Initialize Firebase in project directory
firebase init

# Select:
# - Hosting: Configure files for Firebase Hosting
# - Use existing project: knowledge-rag-prod
# - Public directory: public (we'll create this)
# - Single-page app: No
# - Set up GitHub Actions: No (we have our own)
```

### Create Public Directory Structure

```powershell
# Create public directory
New-Item -ItemType Directory -Force -Path public

# Copy static assets (if you have custom HTML)
# Or use the Firebase rewrite to serve everything from Cloud Run
```

### Configure firebase.json

Create `firebase.json`:

```json
{
  "hosting": {
    "public": "public",
    "ignore": [
      "firebase.json",
      "**/.*",
      "**/node_modules/**"
    ],
    "rewrites": [
      {
        "source": "/api/**",
        "run": {
          "serviceId": "knowledge-rag",
          "region": "us-central1"
        }
      },
      {
        "source": "/**",
        "run": {
          "serviceId": "knowledge-rag",
          "region": "us-central1"
        }
      }
    ],
    "headers": [
      {
        "source": "/api/**",
        "headers": [
          {
            "key": "Cache-Control",
            "value": "no-cache, no-store, must-revalidate"
          }
        ]
      },
      {
        "source": "**/*.@(js|css)",
        "headers": [
          {
            "key": "Cache-Control",
            "value": "public, max-age=31536000"
          }
        ]
      }
    ]
  }
}
```

### Alternative: Serve Static Files from Firebase, API from Cloud Run

If you want to split static UI and API:

```json
{
  "hosting": {
    "public": "public",
    "ignore": ["firebase.json", "**/.*", "**/node_modules/**"],
    "rewrites": [
      {
        "source": "/api/**",
        "run": {
          "serviceId": "knowledge-rag",
          "region": "us-central1"
        }
      }
    ]
  }
}
```

Then copy `templates/index.html` to `public/index.html` and update API URLs.

## Step 5: Deploy to Firebase Hosting

```powershell
# Deploy
firebase deploy --only hosting

# Get hosting URL
firebase hosting:channel:deploy live
```

Your app is now live at: `https://knowledge-rag-prod.web.app`

## Step 6: Custom Domain (Optional)

### Add Custom Domain

```powershell
# Via Firebase Console
# 1. Go to Firebase Console → Hosting
# 2. Click "Add custom domain"
# 3. Enter your domain (e.g., knowledge-rag.com)
# 4. Verify ownership via DNS TXT record
# 5. Add DNS A/AAAA records as shown

# Or via CLI
firebase hosting:sites:create knowledge-rag
```

### SSL Certificate

Firebase automatically provisions SSL certificates for custom domains (no action needed).

## Step 7: Configure GitHub Actions for Automatic Deployment

The repository already includes `.github/workflows/deploy.yml`. Configure these GitHub secrets:

```powershell
# Create a service account for GitHub Actions
gcloud iam service-accounts create github-actions `
  --display-name="GitHub Actions Deployment"

# Grant necessary permissions
gcloud projects add-iam-policy-binding knowledge-rag-prod `
  --member="serviceAccount:github-actions@knowledge-rag-prod.iam.gserviceaccount.com" `
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding knowledge-rag-prod `
  --member="serviceAccount:github-actions@knowledge-rag-prod.iam.gserviceaccount.com" `
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding knowledge-rag-prod `
  --member="serviceAccount:github-actions@knowledge-rag-prod.iam.gserviceaccount.com" `
  --role="roles/iam.serviceAccountUser"

# Create workload identity pool (for keyless auth)
gcloud iam workload-identity-pools create github `
  --location="global" `
  --display-name="GitHub Actions Pool"

# Create provider
gcloud iam workload-identity-pools providers create-oidc github `
  --location="global" `
  --workload-identity-pool="github" `
  --issuer-uri="https://token.actions.githubusercontent.com" `
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" `
  --attribute-condition="assertion.repository_owner=='skepee-PROTOTYPE'"

# Allow GitHub Actions to impersonate service account
$REPO="skepee-PROTOTYPE/knowledge-rag"
gcloud iam service-accounts add-iam-policy-binding `
  github-actions@knowledge-rag-prod.iam.gserviceaccount.com `
  --role="roles/iam.workloadIdentityUser" `
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github/attribute.repository/${REPO}"

# Get the Workload Identity Provider name
$WI_PROVIDER = gcloud iam workload-identity-pools providers describe github `
  --location="global" `
  --workload-identity-pool="github" `
  --format="value(name)"

echo "Add these to GitHub Secrets:"
echo "GCP_PROJECT_ID: knowledge-rag-prod"
echo "GCP_SERVICE_ACCOUNT: github-actions@knowledge-rag-prod.iam.gserviceaccount.com"
echo "GCP_WORKLOAD_IDENTITY_PROVIDER: $WI_PROVIDER"
```

### Add GitHub Secrets

1. Go to your GitHub repository
2. Settings → Secrets and variables → Actions → New repository secret
3. Add:
   - `GCP_PROJECT_ID` = `knowledge-rag-prod`
   - `GCP_SERVICE_ACCOUNT` = `github-actions@knowledge-rag-prod.iam.gserviceaccount.com`
   - `GCP_WORKLOAD_IDENTITY_PROVIDER` = (value from command above)

Now every push to `main` will automatically deploy to Cloud Run!

## Step 8: Enable Persistent Storage for ChromaDB

### Option A: Cloud Storage FUSE (Preview)

```powershell
# Create bucket
gsutil mb -l us-central1 gs://knowledge-rag-cache

# Update Cloud Run deployment to mount bucket
gcloud run deploy knowledge-rag `
  --image gcr.io/knowledge-rag-prod/knowledge-rag `
  --execution-environment gen2 `
  --add-volume name=cache,type=cloud-storage,bucket=knowledge-rag-cache `
  --add-volume-mount volume=cache,mount-path=/app/cache `
  --region us-central1
```

### Option B: Cloud SQL + pgvector (for larger scale)

For production with high traffic, consider migrating to a managed vector database.

## Step 9: Monitoring and Logging

### View Logs

```powershell
# Stream logs
gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=knowledge-rag" --format=json

# View in Console
# https://console.cloud.google.com/logs
```

### Create Alerts

```powershell
# Create alert for high error rate
gcloud alpha monitoring policies create `
  --notification-channels=YOUR_CHANNEL_ID `
  --display-name="High Error Rate - Knowledge RAG" `
  --condition-display-name="Error rate > 5%" `
  --condition-threshold-value=0.05 `
  --condition-threshold-duration=60s
```

### Set Up Uptime Checks

```powershell
gcloud monitoring uptime create https-knowledge-rag `
  --display-name="Knowledge RAG Uptime" `
  --resource-type=uptime-url `
  --monitored-resource=https://knowledge-rag-prod.web.app/api/stats `
  --period=60 `
  --timeout=10s
```

## Step 10: Performance Optimization

### Enable CDN for Firebase Hosting

Firebase Hosting includes automatic global CDN — no configuration needed!

### Cloud Run Optimization

```powershell
# Update for better cold start performance
gcloud run services update knowledge-rag `
  --region us-central1 `
  --min-instances 1 `
  --cpu-boost `
  --execution-environment gen2
```

### Cost Optimization

```powershell
# For dev/staging: reduce resources
gcloud run services update knowledge-rag `
  --region us-central1 `
  --memory 512Mi `
  --cpu 1 `
  --min-instances 0 `
  --max-instances 3
```

## Maintenance

### Update Application

```powershell
# Rebuild and deploy
gcloud builds submit --tag gcr.io/knowledge-rag-prod/knowledge-rag
gcloud run deploy knowledge-rag --image gcr.io/knowledge-rag-prod/knowledge-rag --region us-central1
```

### Rollback

```powershell
# List revisions
gcloud run revisions list --service knowledge-rag --region us-central1

# Route traffic to previous revision
gcloud run services update-traffic knowledge-rag `
  --to-revisions REVISION_NAME=100 `
  --region us-central1
```

### Backup ChromaDB

```powershell
# If using Cloud Storage volume
gsutil -m rsync -r gs://knowledge-rag-cache gs://knowledge-rag-backups/$(Get-Date -Format "yyyyMMdd")

# Schedule backups with Cloud Scheduler
gcloud scheduler jobs create http backup-chroma `
  --schedule="0 2 * * *" `
  --uri="$SERVICE_URL/admin/backup" `
  --http-method=POST `
  --oidc-service-account-email=github-actions@knowledge-rag-prod.iam.gserviceaccount.com
```

## Security Checklist

- [x] Secrets stored in Secret Manager
- [x] HTTPS enabled (automatic via Firebase/Cloud Run)
- [x] Rate limiting implemented in code
- [x] Security headers configured (wsgi_prod.py)
- [x] Input validation on all endpoints
- [x] Logging configured (no sensitive data logged)
- [ ] Enable GitHub secret scanning
- [ ] Enable Dependabot
- [ ] Configure CORS if needed for specific domains
- [ ] Set up alerting for security events
- [ ] Regular dependency updates

## Costs (Estimated)

**Free Tier Eligible:**
- Firebase Hosting: 10GB storage, 360MB/day transfer
- Cloud Run: 2M requests/month, 360k CPU-seconds, 180k memory-seconds
- Secret Manager: 6 active secret versions

**Beyond Free Tier (approximate):**
- Cloud Run: ~$0.40/million requests
- Cloud Storage: ~$0.020/GB/month
- Egress: ~$0.12/GB (after 1GB free)

For low-moderate traffic, costs should be < $10/month.

## Troubleshooting

### Cloud Run deployment fails

```powershell
# Check build logs
gcloud builds list --limit=5
gcloud builds log BUILD_ID

# Check service logs
gcloud logging read "resource.type=cloud_run_revision" --limit 50
```

### Secrets not accessible

```powershell
# Verify IAM binding
gcloud secrets get-iam-policy github-token

# Test secret access
gcloud secrets versions access latest --secret=github-token
```

### Firebase rewrite not working

- Ensure Cloud Run service is `--allow-unauthenticated`
- Check firebase.json syntax
- Clear browser cache
- Check Firebase Hosting logs in console

## Next Steps

1. ✅ Test production deployment end-to-end
2. ✅ Monitor logs for errors
3. ✅ Set up alerts for downtime/errors
4. ✅ Configure backups
5. ✅ Add custom domain (optional)
6. ✅ Enable GitHub secret scanning
7. ✅ Plan capacity/scaling based on traffic
8. ✅ Consider migrating to managed vector DB for scale

## Resources

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Firebase Hosting](https://firebase.google.com/docs/hosting)
- [Secret Manager](https://cloud.google.com/secret-manager/docs)
- [Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation)
