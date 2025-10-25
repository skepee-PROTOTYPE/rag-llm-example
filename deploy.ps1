# Quick Deploy to Firebase + Cloud Run
# This script automates the deployment process

param(
    [Parameter(Mandatory=$true)]
    [string]$ProjectId,
    
    [Parameter(Mandatory=$true)]
    [string]$GitHubToken,
    
    [string]$Region = "us-central1",
    [string]$ServiceName = "knowledge-rag"
)

Write-Host "🚀 Knowledge RAG - Firebase + Cloud Run Deployment" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Set project
Write-Host "📋 Setting GCP project to $ProjectId..." -ForegroundColor Yellow
gcloud config set project $ProjectId

# Enable required APIs
Write-Host "🔧 Enabling required APIs..." -ForegroundColor Yellow
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable firebase.googleapis.com

# Store secret
Write-Host "🔐 Storing GitHub token in Secret Manager..." -ForegroundColor Yellow
$secretExists = gcloud secrets list --filter="name:github-token" --format="value(name)"
if ($secretExists) {
    Write-Host "   Secret already exists, creating new version..." -ForegroundColor Gray
    echo -n $GitHubToken | gcloud secrets versions add github-token --data-file=-
} else {
    Write-Host "   Creating new secret..." -ForegroundColor Gray
    echo -n $GitHubToken | gcloud secrets create github-token --data-file=-
}

# Grant Cloud Run access to secret
Write-Host "🔑 Granting Cloud Run access to secrets..." -ForegroundColor Yellow
$projectNumber = gcloud projects describe $ProjectId --format="value(projectNumber)"
gcloud secrets add-iam-policy-binding github-token `
    --member="serviceAccount:${projectNumber}-compute@developer.gserviceaccount.com" `
    --role="roles/secretmanager.secretAccessor" `
    --quiet

# Build and deploy
Write-Host "🏗️  Building container..." -ForegroundColor Yellow
gcloud builds submit --tag gcr.io/$ProjectId/$ServiceName

Write-Host "🚢 Deploying to Cloud Run..." -ForegroundColor Yellow
gcloud run deploy $ServiceName `
    --image gcr.io/$ProjectId/$ServiceName `
    --platform managed `
    --region $Region `
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
$serviceUrl = gcloud run services describe $ServiceName --region $Region --format 'value(status.url)'

Write-Host ""
Write-Host "✅ Deployment Complete!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Service URL: $serviceUrl" -ForegroundColor White
Write-Host ""

# Test endpoints
Write-Host "🧪 Testing endpoints..." -ForegroundColor Yellow
Write-Host "Testing stats endpoint..." -ForegroundColor Gray
$statsResponse = curl -s "$serviceUrl/api/stats"
Write-Host "Stats: $statsResponse" -ForegroundColor White
Write-Host ""

Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "1. Test your deployment: $serviceUrl" -ForegroundColor White
Write-Host "2. Configure Firebase Hosting: firebase init" -ForegroundColor White
Write-Host "3. Deploy hosting: firebase deploy --only hosting" -ForegroundColor White
Write-Host "4. Set up monitoring and alerts" -ForegroundColor White
Write-Host "5. Configure GitHub Actions secrets for auto-deployment" -ForegroundColor White
Write-Host ""
Write-Host "Documentation:" -ForegroundColor Cyan
Write-Host "- Full guide: FIREBASE_DEPLOYMENT.md" -ForegroundColor White
Write-Host "- Security: SECURITY.md" -ForegroundColor White
Write-Host "- Production setup: PRODUCTION_DEPLOYMENT.md" -ForegroundColor White
