# School Management

A Dockerized school management system with FastAPI, PostgreSQL, Redis, Grafana, Loki, Promtail, and SonarQube.

## Prerequisites

* Ubuntu 20.04+
* Git
* Docker & Docker Compose

## 1️⃣. Clone the Repository

git clone https://github.com/DineshKumar9412/final_school_management_api.git

### Change Dirctory
cd final_school_management_api

## 2️⃣. Install Docker and Docker Compose
sudo apt update

sudo apt upgrade -y

sudo apt install -y apt-transport-https ca-certificates curl software-properties-common lsb-release

curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
  
sudo apt update

sudo apt install -y docker-ce docker-ce-cli containerd.io

sudo apt update

sudo apt install -y docker-compose-plugin

### Check installation:
docker --version

docker compose version

## 3️⃣. Create `.env` File

### Create a `.env` file in the project root:

#### # DATABASE

DB_USER="root"

DB_PASSWORD="Root@123"

DB_HOST="localhost"

DB_NAME="sampledb"

DB_PORT="3306"

#### # REDIS

REDIS_HOST="127.0.0.1"

REDIS_PORT="6379"

REDIS_PASSWORD="Redis@123"

#### # ENCRYPTION KEY

KEY="MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="

IV="YWJjZGVmOTg3NjU0MzIxMA==" 

#### # SONAR TOKEN 

SONAR_TOKEN="squ_f432f3d48f716e518958d90e29c27bb64bbbf7eb"

## 4️⃣. Run Docker Compose 
### HOW TO START FASTAPI FIRST
sudo docker build -t school-app:latest ./school_app

sudo docker compose up -d school-app

### HOW TO RUN DOCKER COMPOSE
cd infra/preprod

sudo docker compose up -d

### Build the app container if needed:
sudo docker compose build

### Check logs for troubleshooting:

sudo docker compose logs -f

### CHECK OLD LOG
sudo docker logs school-app-preprod

sudo docker logs -f --tail 100 school-app-preprod

sudo docker logs -f --tail 100 loki-preprod

### Check running containers:
sudo docker ps

### Stop all services:
sudo docker compose down

sudo docker compose down -v

### Remove all Docker Compose
sudo docker compose down --remove-orphans

### check Log
sudo docker logs school-app-preprod

## 5️⃣. Access Applications 

* **FastAPI Docs:** `http://<server-ip>:8000/docs`
* **Grafana:** `http://<server-ip>:3000`
* **SonarQube:** `http://<server-ip>:9000`
* **Prometheus:** `http://<server-ip>:9090`

> **Note:** To connect Grafana to Loki, add the Loki endpoint: `http://loki:3100`.

> **Note:** To connect Grafana to Prometheus, add the Prometheus endpoint: `http://prometheus:9090`.

## 6️⃣. Additional Notes 

* Ensure volumes are persisted correctly for Grafana, SonarQube, and Loki.
* Adjust `.env` file as needed for your database and Redis credentials.

## 7️⃣ Without Docker how to check 

### instal python 3.10
sudo apt update

sudo apt install software-properties-common -y

sudo add-apt-repository ppa:deadsnakes/ppa

sudo apt update

sudo apt install python3.10 python3.10-venv python3.10-dev -y

python3.10 --version

### create a ENV
#### Create a virtual environment named 'school_env' using Python 3.10
python3.10 -m venv school_env

source school_env/bin/activate
#### Upgrade pip to the latest version
pip install --upgrade pip
#### Install all dependencies listed in requirements.txt
pip install -r requirements.txt
#### Run the FastAPI app using Uvicorn on all network interfaces (0.0.0.0) at port 8000
uvicorn main:app --reload --host 0.0.0.0 --port 8000
#### List all processes listening on network ports (to check if your app is running)
sudo lsof -i -P -n | grep LISTEN
## 8️⃣ BEFORE SonarQube

pip install ruff black mypy

ruff check school_app

black --check school_app

mypy school_app

## 9️⃣ HOW TO INSTALL JENKINS
sudo apt install -y openjdk-17-jdk

curl -fsSL https://pkg.jenkins.io/debian-stable/jenkins.io-2023.key | sudo tee \
  /usr/share/keyrings/jenkins-keyring.asc > /dev/null

echo deb [signed-by=/usr/share/keyrings/jenkins-keyring.asc] \
https://pkg.jenkins.io/debian-stable binary/ | sudo tee \
/etc/apt/sources.list.d/jenkins.list > /dev/null

sudo apt update

sudo apt install -y jenkins

sudo systemctl enable jenkins

sudo systemctl start jenkins

http://<SERVER_IP>:8080

sudo cat /var/lib/jenkins/secrets/initialAdminPassword

sudo sysctl -w vm.max_map_count=524288

sudo sysctl -w fs.file-max=131072

sudo docker run --rm \
  -e SONAR_HOST_URL="http://13.233.174.10:9000" \
  -e SONAR_LOGIN="squ_dc7b1a4e3f8943719467a3f2492ce0c544e07ed6" \
  -v "/home/ubuntu/final_school_management_api:/usr/src" \
  sonarsource/sonar-scanner-cli

🔟 
