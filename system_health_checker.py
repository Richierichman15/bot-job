#!/usr/bin/env python3
import os
import logging
import psutil
import shutil
import requests
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("system_health_checker")

# Load environment variables
load_dotenv()

class SystemHealthChecker:
    """
    A class to check the health of the system before running critical operations
    """
    
    def __init__(self, error_notifier=None):
        """
        Initialize the SystemHealthChecker
        
        Args:
            error_notifier: Optional error notifier to send alerts
        """
        self.error_notifier = error_notifier
        
        # Set thresholds from environment variables or use defaults
        self.disk_space_threshold = float(os.getenv("DISK_SPACE_THRESHOLD", "0.1"))  # 10% free
        self.memory_threshold = float(os.getenv("MEMORY_THRESHOLD", "0.1"))  # 10% free
        self.cpu_threshold = float(os.getenv("CPU_THRESHOLD", "0.9"))  # 90% usage max
        
        # Internet connectivity check URL
        self.connectivity_check_url = os.getenv("CONNECTIVITY_CHECK_URL", "https://www.google.com")
        
        # Paths to check for existence
        self.required_paths = os.getenv("REQUIRED_PATHS", "applications,config.json").split(",")
        
        logger.info("SystemHealthChecker initialized")
    
    def check_system_health(self):
        """
        Check the health of the system
        
        Returns:
            bool: True if system is healthy, False otherwise
        """
        # Perform checks
        disk_check = self._check_disk_space()
        memory_check = self._check_memory()
        cpu_check = self._check_cpu()
        connectivity_check = self._check_internet_connectivity()
        path_check = self._check_required_paths()
        
        # All checks must pass
        is_healthy = all([
            disk_check,
            memory_check,
            cpu_check,
            connectivity_check,
            path_check
        ])
        
        if is_healthy:
            logger.info("System health check passed")
            return True
        else:
            error_message = "System health check failed"
            logger.error(error_message)
            
            if self.error_notifier:
                self.error_notifier.notify(error_message)
                
            return False
    
    def _check_disk_space(self):
        """
        Check if there is enough free disk space
        
        Returns:
            bool: True if there is enough disk space, False otherwise
        """
        try:
            # Get disk usage for the current directory
            disk_usage = shutil.disk_usage('.')
            free_percent = disk_usage.free / disk_usage.total
            
            if free_percent < self.disk_space_threshold:
                logger.error(f"Disk space check failed: {free_percent:.2%} free, threshold is {self.disk_space_threshold:.2%}")
                return False
                
            logger.info(f"Disk space check passed: {free_percent:.2%} free")
            return True
            
        except Exception as e:
            logger.error(f"Error checking disk space: {str(e)}")
            return False
    
    def _check_memory(self):
        """
        Check if there is enough free memory
        
        Returns:
            bool: True if there is enough memory, False otherwise
        """
        try:
            # Get memory usage
            memory = psutil.virtual_memory()
            free_percent = memory.available / memory.total
            
            if free_percent < self.memory_threshold:
                logger.error(f"Memory check failed: {free_percent:.2%} free, threshold is {self.memory_threshold:.2%}")
                return False
                
            logger.info(f"Memory check passed: {free_percent:.2%} free")
            return True
            
        except Exception as e:
            logger.error(f"Error checking memory: {str(e)}")
            return False
    
    def _check_cpu(self):
        """
        Check if CPU usage is within acceptable limits
        
        Returns:
            bool: True if CPU usage is acceptable, False otherwise
        """
        try:
            # Get CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.5) / 100.0
            
            if cpu_percent > self.cpu_threshold:
                logger.error(f"CPU check failed: {cpu_percent:.2%} used, threshold is {self.cpu_threshold:.2%}")
                return False
                
            logger.info(f"CPU check passed: {cpu_percent:.2%} used")
            return True
            
        except Exception as e:
            logger.error(f"Error checking CPU: {str(e)}")
            return False
    
    def _check_internet_connectivity(self):
        """
        Check if the system has internet connectivity
        
        Returns:
            bool: True if the system has internet connectivity, False otherwise
        """
        try:
            # Check internet connectivity
            response = requests.get(self.connectivity_check_url, timeout=5)
            
            if response.status_code != 200:
                logger.error(f"Internet connectivity check failed: Status code {response.status_code}")
                return False
                
            logger.info("Internet connectivity check passed")
            return True
            
        except Exception as e:
            logger.error(f"Error checking internet connectivity: {str(e)}")
            return False
    
    def _check_required_paths(self):
        """
        Check if all required paths exist
        
        Returns:
            bool: True if all required paths exist, False otherwise
        """
        try:
            # Check if required paths exist
            for path in self.required_paths:
                path = path.strip()
                if not path:
                    continue
                    
                if not os.path.exists(path):
                    logger.error(f"Path check failed: {path} does not exist")
                    return False
            
            logger.info("Path check passed")
            return True
            
        except Exception as e:
            logger.error(f"Error checking required paths: {str(e)}")
            return False


# For testing
if __name__ == "__main__":
    checker = SystemHealthChecker()
    is_healthy = checker.check_system_health()
    print(f"System health: {'HEALTHY' if is_healthy else 'UNHEALTHY'}") 