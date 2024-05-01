#!/bin/bash

# Function to check if the operating system is Debian-based
is_debian_based() {
    if [ -e /etc/debian_version ]; then
        echo "[=] This is a Debian-based system."
        return 0 # True
    else
        echo "[=] This is not a Debian-based system."
        return 1 # False
    fi
}

# Function to check if a package is installed, and install it if not
ensure_package_installed() {
    local package_name=$1
    if ! dpkg -l | grep -q "^ii\s*$package_name\s"; then
        echo "[=] Installing $package_name..."
        apt update
        DEBIAN_FRONTEND=noninteractive apt install -y $package_name
        echo "[🗸] $package_name installed successfully."
    else
        echo "[=] $package_name is already installed."
    fi
}

# Function to clone a GitHub repository
clone_github_repo() {
    local repo_url=$1
    local clone_dir=$2
    git clone $repo_url $clone_dir
}

# Function to install a service file
install_service_file() {
    local service_file=$1
    local service_dir="/etc/systemd/system/"
    cp $service_file $service_dir
}

# Function to install an executable
install_executable() {
    local executable=$1
    local executable_dir="/usr/local/bin/"
    cp $executable "$executable_dir/netperf.py"
    chmod +x "$executable_dir/netperf.py"
}

# Function to enable and start a systemd service
enable_and_start_service() {
    local service_name=$1

    # Enable the service
    systemctl enable $service_name

    # Start the service
    systemctl start $service_name

    echo "[🗸] $service_name enabled and started."
}

# Function to create a virtual environment and install requirements
create_virtualenv() {
    local venv_name=$1
    local requirements_file=$2

    # Create virtual environment
    python3 -m venv $venv_name
    chmod +x $venv_name/bin/activate
    # Activate virtual environment
    source $venv_name/bin/activate

    # Install requirements
    pip install -r $requirements_file

    # Deactivate virtual environment
    deactivate
}

# Main function
main() {
    local repo_url="https://github.com/javedh-dev/netperf.git"
    local work_dir="/usr/share/netperf"
    local service_file="./source/netperf.service"
    local executable="./source/main.py"
    local package_names=("python3" "iperf3" "git" "python3-venv" "python3-pip")
    local service_names=("iperf3" "netperf")
    local venv_name=".venv"
    local requirements_file="./source/requirements.txt"
    DEBIAN_FRONTEND=noninteractive 

    mkdir -p $work_dir
    rm -rf $work_dir/*
    cd $work_dir

    if is_debian_based; then
        echo "[=] Debian based system detected..."
    else
        echo "[!] Unsupported distribution for package installation!!!"
        exit 1
    fi
    apt update
    # Ensure required packages are installed
    for package in "${package_names[@]}"; do
        ensure_package_installed $package
    done

    # Clone the GitHub repository
    clone_github_repo $repo_url "source"

    # Install the service file
    install_service_file "${service_file}"

    # Install the executable
    install_executable "${executable}"

    # Create and activate virtual environment, install requirements, then deactivate
    create_virtualenv $venv_name $requirements_file

    cp $work_dir/source/config.yaml $work_dir/config.yaml

    # Ensure required packages are installed
    for service in "${service_names[@]}"; do
        enable_and_start_service $service
    done

    echo "[🗸] Service, executable, and virtual environment created successfully."
    rm -rf $work_dir/source

    echo "[🗸] Installation is successfull. Please update config file at '/usr/share/netperf/config.yaml' and Restart the services once done"
}

# Run the main function
main
