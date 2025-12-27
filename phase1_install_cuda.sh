#!/bin/bash
# Phase 1: CUDA 12.4 Installation Script for Linux
# RTX 4070 Laptop GPU Setup

set -e  # Exit on error

echo "=========================================="
echo "CUDA 12.4 Installation for RTX 4070"
echo "Linux Setup"
echo "=========================================="
echo ""

# Check if already installed
if command -v nvidia-smi &> /dev/null; then
    echo "✓ NVIDIA drivers found"
    nvidia-smi
    echo ""
else
    echo "✗ NVIDIA drivers not found"
    echo "Installing NVIDIA drivers..."
    sudo apt-get update
    sudo apt-get install -y linux-headers-$(uname -r)
    # Note: Driver installation depends on your Linux distribution
    echo "Please install NVIDIA drivers from https://www.nvidia.com/Download/driverDetails.aspx"
    exit 1
fi

# Install CUDA 12.4 via package manager (faster, more reliable)
echo "Installing CUDA 12.4 toolkit via package manager..."
echo ""

# Detect Linux distribution
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
fi

case "$OS" in
    ubuntu|debian)
        echo "Detected Ubuntu/Debian - using apt"
        # Add NVIDIA repository
        sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys A4B469963BF863CC 2>/dev/null || true
        
        # Update and install CUDA
        sudo apt-get update
        sudo apt-get install -y cuda-toolkit-12-4
        
        # Also install driver if needed
        if ! command -v nvidia-smi &> /dev/null; then
            sudo apt-get install -y nvidia-driver-550
            echo "⚠ Driver installed - please reboot for changes to take effect"
        fi
        ;;
    fedora|rhel|centos)
        echo "Detected Fedora/RHEL/CentOS - using yum/dnf"
        sudo dnf config-manager --add-repo https://developer.download.nvidia.com/compute/cuda/repos/rhel8/x86_64/cuda-rhel8.repo 2>/dev/null || true
        sudo dnf clean all
        sudo dnf install -y cuda-toolkit-12-4
        ;;
    *)
        echo "Unsupported distribution. Installing from runfile..."
        cd /tmp
        
        # Try alternative NVIDIA CDN endpoint
        CUDA_URL="https://catalog.ngc.nvidia.com/orgs/nvidia/containers/cuda/versions/12.4.1-devel-ubuntu22.04/gpu/cuda_12.4.1_linux_x86_64_compat_pkg.run"
        if ! wget -q -O cuda_installer.run "$CUDA_URL"; then
            echo "⚠ Could not download CUDA automatically"
            echo "Please download from: https://developer.nvidia.com/cuda-downloads"
            exit 1
        fi
        chmod +x cuda_installer.run
        sudo sh cuda_installer.run --silent --toolkit --toolchain
        ;;
esac

echo "✓ CUDA 12.4 toolkit installation initiated"

# Add to PATH
echo ""
echo "Setting up CUDA environment variables..."
export PATH=/usr/local/cuda-12.4/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda-12.4/lib64:$LD_LIBRARY_PATH

# Add to .bashrc for persistence
if ! grep -q "CUDA_HOME" ~/.bashrc; then
    cat >> ~/.bashrc << 'EOF'

# CUDA 12.4 Environment
export CUDA_HOME=/usr/local/cuda-12.4
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH
EOF
    echo "✓ Added CUDA to ~/.bashrc"
fi

# Verify CUDA installation
echo ""
echo "Verifying CUDA installation..."
nvcc --version
echo ""

# Download cuDNN
echo "Downloading cuDNN 8.9.7..."
cd /tmp

if [ ! -f "cudnn-linux-x86_64-8.9.7.tar.xz" ]; then
    # Note: cuDNN requires login. Download manually from https://developer.nvidia.com/cudnn
    # Or use this command if you have the link
    echo "⚠ cuDNN requires manual download from https://developer.nvidia.com/cudnn"
    echo "After downloading, run:"
    echo "  tar -xf cudnn-linux-x86_64-8.9.7.tar.xz"
    echo "  sudo cp cudnn-linux-x86_64-8.9.7/include/* /usr/local/cuda-12.4/include/"
    echo "  sudo cp cudnn-linux-x86_64-8.9.7/lib/* /usr/local/cuda-12.4/lib64/"
else
    echo "Installing cuDNN..."
    tar -xf cudnn-linux-x86_64-8.9.7.tar.xz
    sudo cp cudnn-linux-x86_64-8.9.7/include/* /usr/local/cuda-12.4/include/
    sudo cp cudnn-linux-x86_64-8.9.7/lib/* /usr/local/cuda-12.4/lib64/
    echo "✓ cuDNN installed"
fi

echo ""
echo "=========================================="
echo "✓ Phase 1 CUDA Installation Complete!"
echo "=========================================="
echo ""
echo "Next step: Run install_python_packages.sh"
