# 🏗️ Architecture Documentation

## System Architecture

### High-Level Overview
```
┌─────────────────────────────────────────────────────────────┐
│                         User Browser                         │
└────────────────────────────┬────────────────────────────────┘
                             │
                   ┌─────────▼─────────┐
                   │  Nginx Ingress    │
                   │  (meal-prep.local)│
                   └─────────┬─────────┘
                             │
                   ┌─────────▼─────────┐
                   │   Frontend        │
                   │   (2 replicas)    │
                   └─────────┬─────────┘
                             │
                   ┌─────────▼─────────┐
                   │   Backend API     │
                   │   (3 replicas)    │
                   └─────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
    ┌─────────▼───────┐     │     ┌────────▼────────┐
    │   PostgreSQL    │     │     │  USDA API       │
    │   (StatefulSet) │     │     │  (External)     │
    └─────────────────┘     │     └─────────────────┘
                            │
                   ┌────────▼────────┐
                   │   Prometheus    │
                   │   (Monitoring)  │
                   └────────┬────────┘
                            │
                   ┌────────▼────────┐
                   │    Grafana      │
                   │   (Dashboards)  │
                   └─────────────────┘
```

### CI/CD Pipeline
```
┌──────────────┐
│  Developer   │
└──────┬───────┘
       │ git push
       ▼
┌──────────────┐
│    GitHub    │
└──────┬───────┘
       │ webhook
       ▼
┌──────────────┐
│GitHub Actions│
│   (CI/CD)    │
└──────┬───────┘
       │
       ├─▶ Lint Code
       ├─▶ Build Docker Images
       └─▶ Push to Docker Hub
             │
             ▼
       ┌──────────────┐
       │  Docker Hub  │
       └──────┬───────┘
              │
              ▼
       ┌──────────────┐
       │   ArgoCD     │
       │  (watches)   │
       └──────┬───────┘
              │ auto-sync
              ▼
       ┌──────────────┐
       │  Kubernetes  │
       │   Cluster    │
       └──────────────┘
```

## Component Details

### Frontend Service
- **Type**: Deployment
- **Replicas**: 2
- **Port**: 3000
- **Language**: Python/Flask
- **Purpose**: User interface, form handling

### Backend Service
- **Type**: Deployment
- **Replicas**: 3
- **Port**: 5000
- **Language**: Python/Flask
- **Purpose**: Business logic, API integration, data processing

### Database Service
- **Type**: StatefulSet
- **Replicas**: 1
- **Port**: 5432
- **Database**: PostgreSQL 14
- **Storage**: Persistent Volume (10GB)
- **Purpose**: Data persistence

### Monitoring Stack
- **Prometheus**: Metrics collection (30s intervals)
- **Grafana**: Visualization dashboards
- **Node Exporter**: System metrics
- **Kube State Metrics**: Kubernetes metrics

## Data Flow

### Search Request
```
1. User enters food name in browser
2. Frontend sends POST to /search
3. Backend queries USDA API
4. Backend saves results to PostgreSQL
5. Backend returns formatted data
6. Frontend displays results
7. Prometheus records metrics
```

### Resource Limits

| Component | CPU Request | CPU Limit | Memory Request | Memory Limit |
|-----------|-------------|-----------|----------------|--------------|
| Frontend  | 100m        | 500m      | 128Mi          | 256Mi        |
| Backend   | 100m        | 500m      | 256Mi          | 512Mi        |
| Database  | 100m        | 1000m     | 256Mi          | 512Mi        |

## Network Policies

- Frontend → Backend: Port 5000 (allowed)
- Backend → Database: Port 5432 (allowed)
- Backend → Internet: HTTPS (USDA API)
- External → Frontend: Port 80 (via Ingress)
- All else: Denied (default)

## High Availability

- **Frontend**: 2 replicas, rolling updates
- **Backend**: 3 replicas, rolling updates
- **Database**: StatefulSet with persistent storage
- **Load Balancing**: Kubernetes Services (ClusterIP)
- **Health Checks**: Liveness & readiness probes

## Disaster Recovery

- **Git**: All configurations version controlled
- **S3**: Terraform state backed up
- **ArgoCD**: Automatic sync from Git
- **Database**: Persistent volumes (survives pod restarts)
