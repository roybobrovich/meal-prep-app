# 🍽️ Meal Prep Calculator - Full-Stack DevOps Project

A production-grade meal preparation calculator application demonstrating modern DevOps practices and cloud-native architecture.

![Project Status](https://img.shields.io/badge/status-production-green)
![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-blue)
![GitOps](https://img.shields.io/badge/GitOps-ArgoCD-orange)
![IaC](https://img.shields.io/badge/IaC-Terraform-purple)

## 🎯 Project Overview

Calculate nutritional information for meal prep using real USDA food data. Built with microservices architecture and deployed using GitOps principles.

**Live Demo:** http://meal-prep.local (when running locally)

## 🏗️ Architecture
```
┌─────────────┐      ┌─────────────┐      ┌──────────────┐
│   Frontend  │─────▶│   Backend   │─────▶│  PostgreSQL  │
│  (Flask)    │◀─────│   (Flask)   │◀─────│   Database   │
└─────────────┘      └─────────────┘      └──────────────┘
       │                    │                      │
       └────────────────────┴──────────────────────┘
                            │
                    ┌───────▼────────┐
                    │  USDA FoodData │
                    │   Central API  │
                    └────────────────┘
```

**Deployment Architecture:**
```
Developer → Git Push → GitHub Actions → Docker Hub
                              ↓
                         ArgoCD Sync
                              ↓
                    Kubernetes Cluster
                              ↓
                    ┌─────────┴─────────┐
                    │                   │
               Prometheus            Grafana
              (Monitoring)         (Dashboards)
```

## 🚀 Features

- 🔍 **Food Search**: Search USDA database with 1M+ foods
- 📊 **Nutrition Analysis**: Detailed macro and micronutrient breakdown
- 🍱 **Meal Planning**: Calculate totals for multiple ingredients
- �� **Persistent Storage**: Save searches and meal plans
- 📈 **Real-time Monitoring**: Track application health and performance

## 🛠️ Technology Stack

### **Application**
- **Frontend**: Flask, Jinja2, HTML/CSS
- **Backend**: Flask, Python 3.11, RESTful API
- **Database**: PostgreSQL 14
- **External API**: USDA FoodData Central

### **DevOps & Infrastructure**
- **Containerization**: Docker (multi-stage builds)
- **Orchestration**: Kubernetes, Helm Charts
- **CI/CD**: GitHub Actions
- **GitOps**: ArgoCD
- **Monitoring**: Prometheus + Grafana
- **IaC**: Terraform
- **Cloud**: AWS (S3, DynamoDB, IAM)
- **Registry**: Docker Hub

## 📊 DevOps Pipeline
```
Code Commit
    ↓
GitHub Actions CI
    ├─ Lint (flake8)
    └─ Build Docker Images
        ↓
    Push to Docker Hub
    (tagged: commit-hash, latest)
        ↓
    Update Git (GitOps repo)
        ↓
    ArgoCD Detects Change
        ↓
    Auto-Deploy to K8s
        ↓
    Prometheus Monitors
        ↓
    Grafana Visualizes
```

## 🏃 Quick Start

### **Prerequisites**
- minikube
- kubectl
- helm
- Docker

### **Deploy Everything**
```bash
# 1. Start minikube
minikube start

# 2. Install ArgoCD
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# 3. Deploy applications via ArgoCD
kubectl apply -f https://raw.githubusercontent.com/roybobrovich/meal-prep-gitops/main/apps/

# 4. Wait for deployment
kubectl get pods -w

# 5. Access application
echo "$(minikube ip) meal-prep.local" | sudo tee -a /etc/hosts
```

**Access URLs:**
- Application: http://meal-prep.local
- Grafana: http://grafana.meal-prep.local
- ArgoCD: https://argocd.meal-prep.local

## 📁 Repository Structure

This project follows a multi-repository architecture:

- **[meal-prep-app](https://github.com/roybobrovich/meal-prep-app)** (this repo)
  - Application source code
  - Helm charts
  - CI/CD pipelines
  
- **[meal-prep-gitops](https://github.com/roybobrovich/meal-prep-gitops)**
  - ArgoCD Application definitions
  - Environment configurations
  - GitOps workflows
  
- **[meal-prep-infrastructure](https://github.com/roybobrovich/meal-prep-infrastructure)**
  - Terraform infrastructure code
  - AWS backend configuration
  - Cloud resources

## 🔐 Security Features

- ✅ Branch protection (main branch)
- ✅ Pull request workflow
- ✅ Automated code quality checks
- ✅ Container image scanning
- ✅ Least-privilege IAM
- ✅ Encrypted secrets
- ✅ Network policies

## 📈 Monitoring & Observability

- **Prometheus**: Collects metrics from all services
- **Grafana**: 15+ pre-built dashboards
- **Metrics tracked**:
  - CPU/Memory usage
  - Request latency
  - Error rates
  - Database connections
  - API response times

## 💰 Cost

**Total Monthly Cost: <$0.01**
- Minikube: FREE (local)
- Docker Hub: FREE (public images)
- GitHub Actions: FREE (public repo)
- AWS S3/DynamoDB: ~$0.01/month

## 🎓 What This Project Demonstrates

✅ **Microservices Architecture**  
✅ **Container Orchestration**  
✅ **CI/CD Automation**  
✅ **GitOps Principles**  
✅ **Infrastructure as Code**  
✅ **Monitoring & Observability**  
✅ **Cloud Engineering**  
✅ **Security Best Practices**  
✅ **Professional Git Workflow**  

## 🤝 Contributing

This is a portfolio/learning project, but feedback is welcome!

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

MIT License - See LICENSE file for details

## 👤 Author

**Roy Bobrovich**
- GitHub: [@roybobrovich](https://github.com/roybobrovich)
- LinkedIn: [Add your LinkedIn]

## 🙏 Acknowledgments

- USDA FoodData Central API
- Anthropic Claude (development assistant)
- Open source community

---

