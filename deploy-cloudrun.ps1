#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Deploy RAG application to Google Cloud Run
.DESCRIPTION
    Automated deployment script for Flask RAG API to Cloud Run
.PARAMETER ProjectId
    GCP Project ID
.PARAMETER GitHubToken
    GitHub Personal Access Token for API access
.PARAMETER Region
    GCP region (default: us-central1)
.PARAMETER ServiceName
    Cloud Run service name (default: rag-api)
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$ProjectId,
    
    [Parameter(Mandatory=$true)]
    [string]$GitHubToken,
    
    [Parameter(Mandatory=$false)]
    [string]$Region = "us-central1",
    
    [Parameter(Mandatory=$false)]
    [string]$ServiceName = "rag-api"
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "==> RAG API - Cloud Run Deployment" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

# Check prerequisites
Write-Host "[CHECK] Checking prerequisites..." -ForegroundColor Yellow
$prerequisites = @("gcloud", "docker")
foreach ($cmd in $prerequisites) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Host "[ERROR] $cmd is not installed" -ForegroundColor Red
        exit 1
    }
}
Write-Host "[OK] Prerequisites satisfied" -ForegroundColor Green

# Set GCP project
Write-Host "[SETUP] Setting GCP project to $ProjectId..." -ForegroundColor Yellow
gcloud config set project $ProjectId

# Enable required APIs
Write-Host "[SETUP] Enabling required APIs..." -ForegroundColor Yellow
gcloud services enable run.googleapis.com --quiet
gcloud services enable cloudbuild.googleapis.com --quiet
gcloud services enable secretmanager.googleapis.com --quiet
gcloud services enable containerregistry.googleapis.com --quiet

# Store GitHub token in Secret Manager
Write-Host "[SECRETS] Storing GitHub token in Secret Manager..." -ForegroundColor Yellow
$secretExists = gcloud secrets describe github-token --format="value(name)" 2>$null
if ($secretExists) {
    Write-Host "   Updating existing secret..." -ForegroundColor Gray
    Write-Output $GitHubToken | gcloud secrets versions add github-token --data-file=-
} else {
    Write-Host "   Creating new secret..." -ForegroundColor Gray
    Write-Output $GitHubToken | gcloud secrets create github-token --data-file=-
}

# Grant Cloud Run access to secrets
Write-Host "[SECRETS] Granting Cloud Run access to secrets..." -ForegroundColor Yellow
$projectNumber = gcloud projects describe $ProjectId --format="value(projectNumber)"
$serviceAccount = "$projectNumber-compute@developer.gserviceaccount.com"
gcloud secrets add-iam-policy-binding github-token `
    --member="serviceAccount:$serviceAccount" `
    --role="roles/secretmanager.secretAccessor"

# Build and submit container
Write-Host "[BUILD] Building container (this may take a few minutes)..." -ForegroundColor Yellow
gcloud builds submit --tag gcr.io/$ProjectId/$ServiceName

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Build failed" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Container built successfully" -ForegroundColor Green

# Deploy to Cloud Run
Write-Host "[DEPLOY] Deploying to Cloud Run..." -ForegroundColor Yellow
gcloud run deploy $ServiceName `
    --image gcr.io/$ProjectId/$ServiceName `
    --platform managed `
    --region $Region `
    --allow-unauthenticated `
    --set-env-vars="PORT=8080" `
    --set-secrets="GITHUB_TOKEN=github-token:latest" `
    --memory 512Mi `
    --cpu 1 `
    --max-instances 10 `
    --timeout 60

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Deployment failed" -ForegroundColor Red
    exit 1
}

# Get service URL
$serviceUrl = gcloud run services describe $ServiceName --platform managed --region $Region --format="value(status.url)"

Write-Host ""
Write-Host "[SUCCESS] Deployment Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Service URL: $serviceUrl" -ForegroundColor Cyan
Write-Host ""
Write-Host "[TEST] Testing endpoints..." -ForegroundColor Yellow

# Test health endpoint
Write-Host "  Testing GET $serviceUrl/" -ForegroundColor Gray
$healthResponse = Invoke-RestMethod -Uri "$serviceUrl/" -Method Get
Write-Host "  Status: $($healthResponse.status)" -ForegroundColor Green
Write-Host "  Chunks loaded: $($healthResponse.chunks_loaded)" -ForegroundColor Green

Write-Host ""
Write-Host "[INFO] Available endpoints:" -ForegroundColor Cyan
Write-Host "  GET  $serviceUrl/          - Health check" -ForegroundColor White
Write-Host "  POST $serviceUrl/api/ask   - Ask a question" -ForegroundColor White
Write-Host "  GET  $serviceUrl/api/stats - Get statistics" -ForegroundColor White
Write-Host ""
Write-Host "[INFO] Example usage:" -ForegroundColor Cyan
Write-Host "  Invoke-RestMethod -Uri '$serviceUrl/api/ask' -Method Post -Body (@{question='What is RAG?'} | ConvertTo-Json) -ContentType 'application/json'" -ForegroundColor White
Write-Host ""
Write-Host "[COSTS] Estimated costs:" -ForegroundColor Yellow
Write-Host "  - First 2M requests/month: FREE" -ForegroundColor Green
Write-Host "  - Additional requests: `$0.40 per million" -ForegroundColor White
Write-Host "  - With light usage: `$0-5/month" -ForegroundColor Green
Write-Host ""
