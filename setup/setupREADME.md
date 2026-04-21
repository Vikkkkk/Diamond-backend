# **System setup instructions:**
---
Lets Start with Installing the following prerequisites
1. Python
2. Docker
3. Docker Compose
4. Pylint
5. Python black formatting


## **1. Python Installation :snake:**
---
### **A. How To Install Python 3.10 on Ubuntu 22.04:**
#### **Step 1 – Open Terminal OR Command Prompt**
First of all, your terminal or command prompt by pressing Ctrl+Alt+T key:
#### **Step 2 – Update APT Package**
In this step, visit your terminal and execute the following command to update Apt package list:
```
sudo apt update
```
#### **Step 3 – Add the deadsnakes PPA**
In this step, execute the following command on your terminal to Add the deadsnakes PPA:
```
sudo add-apt-repository ppa:deadsnakes/ppa
```
When prompted, press `Enter` to continue.
#### **Step 4 – Install Python 3.10**
In this step, execute the following command on your terminal to install python 3.10 on ubuntu:
```
sudo apt install python3.10
```
#### **Step 5 – Verify Python Installation**
In this step, execute the following command on your terminal to verify python 3.10 installation on ubuntu 22.04:
```
python3 -V
```

### **B. How To Install Python 3.10 on Windows:**
To downLoad and install the python 3.10 [Click here](https://www.python.org/ftp/python/3.10.7/Python-3.10.7.tar.xz).


## **2. Docker Installation :whale:**
---
### **A. How To Install Docker 20.10 on Ubuntu 22.04:**
#### **Step 1: Update system repositories**
First of all, open up the terminal by hitting “CTRL+ALT+T” in Ubuntu 22.04 and write out the below-given commands for updating the system repositories:
```
sudo apt update
sudo apt upgrade
```
#### **Step 2: Install required dependencies**
After updating the system packages, the next step is to install required dependencies for Docker:
```
sudo apt install lsb-release ca-certificates apt-transport-https software-properties-common -y
```
#### **Step 3: Adding Docker repository to system sources**
When a Docker repository is added to the system sources, it makes the Docker installation easier and provides faster updates.

To add the Docker repository to the system sources, firstly, import the Docker GPG key required for connecting to the Docker repository:
```
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
```
After doing so, execute the following command for adding the Docker repository to your Ubuntu 22.04 system sources list:
```
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list  /dev/null
```
#### **Step 4: Update system packages**
After adding Docker repository to the system sources, again update the system packages:
```
sudo apt update
```
#### **Step 5: Install Docker on Ubuntu 22.04**
At this point, our Ubuntu 22.04 system is all ready for the Docker installation:
```
sudo apt install docker-ce
```
Note that we are utilizing the “docker-ce” package instead of “docker-ie” as it is supported by the official Docker repository:

Enter “y” to permit the Docker installation to continue:
#### **Step 6: Verify Docker status**
Now, execute the below-given “systemctl” command to verify if the Docker is currently active or not on your system:
```
sudo systemctl status docker
```

### **B. How To Install Docker 20.10 on Windows:**
To download and install the Docker 20.10 [Click here](https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe).

 Docker Compose will be installed along with the Docker desktop application.


## **3. Docker Compose Installation :whale2:**
---
### **A. How To Install Docker Compose 2.10.2 on Ubuntu 22.04:**
#### **Step 1: Download Docker Compose package**
First of all, verify the latest version of the Docker Compose package from the release page. For example, at this moment, the most stable version of Docker Compose is “2.10.2”. 

So, we will create a directory with the help of the following “mkdir” command:
```
mkdir -p ~/.docker/cli-plugins/
```
After doing so, utilize the below-given “curl” command for installing Docker Compose on Ubuntu 22.04:
```
curl -SL https://github.com/docker/compose/releases/download/v2.10.2/docker-compose-linux-x86_64 -o ~/.docker/cli-plugins/docker-compose
```
#### **Step 2: Docker Compose Installation**
In the next step, set the executable permissions to the “docker-compose” command:
```
chmod +x ~/.docker/cli-plugins/docker-compose
```
#### **Step 3: Verify Docker Compose Installation**
In this step, execute the following command on your terminal to verify Docker Compose 2.10.2 installation on ubuntu 22.04:
```
docker compose version
```


## **4. Pylint**
Pylint is a static code analyzer.
Pylint analyses your code without actually running it. It checks for errors, enforces a coding standard, looks for code smells, and can make suggestions about how the code could be refactored. 

```commandline
pip install pylint
```


## **5. Python black formatter**
Black is the uncompromising Python code formatter. By using it, you agree to cede control over minutiae of hand-formatting. In return, Black gives you speed, determinism, and freedom from pycodestyle nagging about formatting. You will save time and mental energy for more important matters.
```commandline
pip install black
```

# **Run the Following script to install everything on Ubuntu  22.04:**
```
chmod +x setup.sh
./setup.sh
```