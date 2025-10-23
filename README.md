# 🍽️ Meal Prep Calculator - DevOps Final Project

A full-stack microservices application demonstrating DevOps best practices including containerization, Kubernetes orchestration, and CI/CD pipelines.

## 📋 Project Overview

The Meal Prep Calculator helps users:
- Search for food nutritional information (via USDA API)
- Build custom meals with multiple ingredients
- Calculate total and per-serving nutritional values
- Save and manage meal history

## 🏗️ Architecture

### Microservices Design
```
┌─────────────┐
│   Frontend  │ (Flask Templates - Port 3000)
└──────┬──────┘
       │
┌──────▼──────┐
│   Backend   │ (Flask API - Port 5000)
└──────┬──────┘
       │
┌──────▼──────┐
│  PostgreSQL │ (Database - Port 5432)
└─────────────┘
```

### Technology Stack

**Frontend:**
- Python Flask
- Jinja2 Templates
- HTML/CSS

**Backend:**
- Python Flask
- SQLAlchemy ORM
- USDA FoodData Central API integration

**Database:**
- PostgreSQL 16
- Persistent storage with volumes

**Infrastructure:**
- Docker & Docker Compose
- Kubernetes (Helm Charts)
- minikube (local testing)

## 🐳 Docker

### Running with Docker Compose

```bash
# Build and start all services
docker-compose up --build

# Access application
Frontend: http://localhost:3000
Backend API: http://localhost:5000
```

### Docker Images

Images are available on DockerHub:
- `roybob/meal-prep-backend:latest`
- `roybob/meal-prep-frontend:latest`
- `postgres:16-alpine` (official)

## ☸️ Kubernetes Deployment

### Prerequisites

- minikube
- kubectl
- helm

### Deploy to Kubernetes

```bash
# Start minikube
minikube start

# Enable ingress
minikube addons enable ingress

# Install Helm charts
helm install meal-prep-db ./helm/database
helm install meal-prep-backend ./helm/backend
helm install meal-prep-frontend ./helm/frontend

# Get ingress IP
kubectl get ingress

# Add to /etc/hosts
echo "$(minikube ip) meal-prep.local" | sudo tee -a /etc/hosts

# Access application
http://meal-prep.local
```

### Helm Charts

Three independent charts for each service:

**Database (StatefulSet):**
- Persistent storage with PVC
- PostgreSQL 16 Alpine
- Resource limits configured

**Backend (Deployment):**
- 2 replicas for high availability
- Health checks (liveness + readiness)
- Environment variables via ConfigMap
- Secrets for sensitive data

**Frontend (Deployment):**
- 2 replicas for load balancing
- Ingress for external access
- Session-based state management

## 📁 Project Structure

```
meal-prep-app/
├── backend/
│   ├── app.py              # Flask API
│   ├── models.py           # SQLAlchemy models
│   ├── requirements.txt    # Python dependencies
│   ├── Dockerfile          # Container image
│   └── .env               # Environment variables
├── frontend/
│   ├── app.py              # Flask web server
│   ├── templates/          # HTML templates
│   ├── static/            # CSS files
│   ├── requirements.txt
│   └── Dockerfile
├── helm/
│   ├── backend/           # Backend Helm chart
│   ├── frontend/          # Frontend Helm chart
│   └── database/          # Database Helm chart
└── docker-compose.yml     # Local development
```

## 🔧 Configuration

### Environment Variables

**Backend:**
```
USDA_API_KEY=your_api_key
USDA_API_URL=https://api.nal.usda.gov/fdc/v1
DB_HOST=meal-prep-db
DB_PORT=5432
DB_NAME=meal_prep_db
DB_USER=postgres
DB_PASSWORD=postgres
```

**Frontend:**
```
BACKEND_URL=http://meal-prep-backend:5000
SECRET_KEY=your_secret_key
PORT=3000
```

## 🧪 Testing

### Local Testing (Docker Compose)
```bash
docker-compose up
# Access: http://localhost:3000
```

### Kubernetes Testing (minikube)
```bash
minikube start
# Deploy helm charts
# Access: http://meal-prep.local
```

### Health Checks

```bash
# Backend health
curl http://localhost:5000/health

# Frontend health
curl http://localhost:3000/health
```

## 📊 API Endpoints

### Backend REST API

```
GET  /health                    - Health check
GET  /api/search?query=chicken  - Search food items
GET  /api/food/{id}            - Get food details
POST /api/calculate            - Calculate nutrition
POST /api/meals                - Save meal
GET  /api/meals                - Get all meals
GET  /api/meals/{id}           - Get specific meal
DELETE /api/meals/{id}         - Delete meal
```

## 🎓 DevOps Practices Demonstrated

✅ **Containerization** - Docker multi-stage builds, optimization
✅ **Orchestration** - Kubernetes with Helm package manager
✅ **Microservices** - Independent, scalable services
✅ **Infrastructure as Code** - Helm charts, declarative configs
✅ **High Availability** - Multiple replicas, health checks
✅ **Resource Management** - CPU/Memory limits and requests
✅ **Networking** - Services, Ingress, internal DNS
✅ **Storage** - Persistent volumes, StatefulSets
✅ **Security** - Secrets management, least privilege

## 📝 Future Enhancements

- [ ] CI/CD Pipeline (GitHub Actions)
- [ ] Terraform for AWS EKS
- [ ] ArgoCD for GitOps
- [ ] Prometheus & Grafana monitoring
- [ ] Horizontal Pod Autoscaling
- [ ] SSL/TLS certificates

## 👤 Author

DevOps Engineering Final Project

## 📄 License

This project is for educational purposes.