"""
Application launcher for Chat Summarization API
Runs both FastAPI backend and Streamlit frontend simultaneously
Provides integrated user experience with both Swagger UI and Streamlit interface
Fixed dependency checking and process management
"""

import os
import sys
import time
import signal
import subprocess
import threading
import webbrowser
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class AppLauncher:
    """
    Application launcher that manages both FastAPI and Streamlit processes
    Handles startup, shutdown, and process management for integrated experience
    """
    
    def __init__(self):
        # Configuration from environment variables
        self.api_host = os.getenv("API_HOST", "0.0.0.0")
        self.api_port = int(os.getenv("API_PORT", 8000))
        self.streamlit_port = int(os.getenv("STREAMLIT_PORT", 8501))
        
        # Process references
        self.fastapi_process = None
        self.streamlit_process = None
        
        # URLs for user access
        self.api_url = f"http://localhost:{self.api_port}"
        self.swagger_url = f"http://localhost:{self.api_port}/docs"
        self.streamlit_url = f"http://localhost:{self.streamlit_port}"
        
        print("🚀 Chat Summarization API Launcher")
        print("=" * 50)
        print(f"FastAPI Backend: {self.api_url}")
        print(f"Swagger UI: {self.swagger_url}")
        print(f"Streamlit Frontend: {self.streamlit_url}")
        print("=" * 50)
    
    def start_fastapi(self):
        """
        Start FastAPI backend server
        Runs uvicorn server for the REST API with LangChain MongoDB integration
        """
        try:
            print("🔧 Starting FastAPI backend...")
            
            # Start FastAPI using uvicorn
            self.fastapi_process = subprocess.Popen([
                sys.executable, "-m", "uvicorn",
                "app:app",
                "--host", self.api_host,
                "--port", str(self.api_port),
                "--reload"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            print(f"✅ FastAPI started on {self.api_url}")
            print(f"📚 Swagger UI available at {self.swagger_url}")
            
        except Exception as e:
            print(f"❌ Error starting FastAPI: {e}")
            return False
        
        return True
    
    def start_streamlit(self):
        """
        Start Streamlit frontend application
        Runs Streamlit web interface for user interaction
        """
        try:
            print("🎨 Starting Streamlit frontend...")
            
            # Start Streamlit
            self.streamlit_process = subprocess.Popen([
                sys.executable, "-m", "streamlit",
                "run", "frontend.py",
                "--server.port", str(self.streamlit_port),
                "--server.address", "0.0.0.0",
                "--server.headless", "true",
                "--browser.gatherUsageStats", "false"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            print(f"✅ Streamlit started on {self.streamlit_url}")
            
        except Exception as e:
            print(f"❌ Error starting Streamlit: {e}")
            return False
        
        return True
    
    def wait_for_services(self):
        """
        Wait for both services to be ready
        Checks if both FastAPI and Streamlit are responding
        """
        import requests
        
        print("⏳ Waiting for services to start...")
        
        # Wait for FastAPI
        for i in range(30):  # 30 second timeout
            try:
                response = requests.get(f"{self.api_url}/", timeout=2)
                if response.status_code == 200:
                    print("✅ FastAPI is ready!")
                    break
            except:
                pass
            time.sleep(1)
        else:
            print("⚠️ FastAPI might not be ready yet")
        
        # Wait for Streamlit (just wait a bit as it doesn't have a health endpoint)
        time.sleep(5)
        print("✅ Streamlit should be ready!")
    
    def open_browsers(self):
        """
        Open browser tabs for both interfaces
        Provides easy access to both Swagger UI and Streamlit interface
        """
        try:
            print("🌐 Opening browser tabs...")
            
            # Open Swagger UI for API testing
            webbrowser.open(self.swagger_url)
            
            # Wait a moment then open Streamlit
            time.sleep(2)
            webbrowser.open(self.streamlit_url)
            
            print("✅ Browser tabs opened!")
            
        except Exception as e:
            print(f"⚠️ Could not open browsers automatically: {e}")
            print("Please manually open:")
            print(f"  - Swagger UI: {self.swagger_url}")
            print(f"  - Streamlit: {self.streamlit_url}")
    
    def setup_signal_handlers(self):
        """
        Setup signal handlers for graceful shutdown
        Ensures both processes are properly terminated on exit
        """
        def signal_handler(signum, frame):
            print("\n🛑 Shutting down applications...")
            self.shutdown()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def shutdown(self):
        """
        Gracefully shutdown both applications
        Terminates FastAPI and Streamlit processes
        """
        try:
            if self.fastapi_process:
                print("🛑 Stopping FastAPI...")
                self.fastapi_process.terminate()
                self.fastapi_process.wait(timeout=5)
                print("✅ FastAPI stopped")
        except:
            print("⚠️ Force killing FastAPI...")
            if self.fastapi_process:
                self.fastapi_process.kill()
        
        try:
            if self.streamlit_process:
                print("🛑 Stopping Streamlit...")
                self.streamlit_process.terminate()
                self.streamlit_process.wait(timeout=5)
                print("✅ Streamlit stopped")
        except:
            print("⚠️ Force killing Streamlit...")
            if self.streamlit_process:
                self.streamlit_process.kill()
    
    def display_usage_info(self):
        """
        Display usage information and available interfaces
        Helps users understand how to interact with the application
        """
        print("\n📖 Usage Information:")
        print("=" * 50)
        print("🔧 FastAPI Backend:")
        print(f"   • REST API: {self.api_url}")
        print(f"   • Swagger UI: {self.swagger_url}")
        print("   • Use for API testing and development")
        print("")
        print("🎨 Streamlit Frontend:")
        print(f"   • Web Interface: {self.streamlit_url}")
        print("   • Use for interactive chat and user interface")
        print("")
        print("🚀 Features Available:")
        print("   • 🧠 Memory-enhanced conversations")
        print("   • 📊 AI-powered summarization")
        print("   • ❓ Context-aware Q&A")
        print("   • 🔍 Conversation search")
        print("   • 📚 Chat history management")
        print("   • 🎯 Session-based storage")
        print("")
        print("💡 Quick Start:")
        print("   1. Use Streamlit for easy chat interaction")
        print("   2. Use Swagger UI for API testing")
        print("   3. Press Ctrl+C to stop both services")
        print("=" * 50)
    
    def monitor_processes(self):
        """
        Monitor both processes and restart if they crash
        Ensures application reliability and uptime
        """
        while True:
            try:
                # Check FastAPI process
                if self.fastapi_process and self.fastapi_process.poll() is not None:
                    print("⚠️ FastAPI process died, restarting...")
                    self.start_fastapi()
                
                # Check Streamlit process
                if self.streamlit_process and self.streamlit_process.poll() is not None:
                    print("⚠️ Streamlit process died, restarting...")
                    self.start_streamlit()
                
                time.sleep(5)  # Check every 5 seconds
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"⚠️ Error in process monitoring: {e}")
                time.sleep(5)
    
    def run(self):
        """
        Main method to run the entire application
        Starts both services and manages their lifecycle
        """
        try:
            # Setup signal handlers for graceful shutdown
            self.setup_signal_handlers()
            
            # Start FastAPI backend
            if not self.start_fastapi():
                print("❌ Failed to start FastAPI. Exiting.")
                return
            
            # Start Streamlit frontend
            if not self.start_streamlit():
                print("❌ Failed to start Streamlit. Stopping FastAPI and exiting.")
                self.shutdown()
                return
            
            # Wait for services to be ready
            self.wait_for_services()
            
            # Display usage information
            self.display_usage_info()
            
            # Open browsers (optional)
            try:
                open_browser = input("\n🌐 Open browser tabs automatically? (y/n): ").lower().strip()
                if open_browser in ['y', 'yes', '']:
                    self.open_browsers()
            except KeyboardInterrupt:
                pass
            
            print("\n🎯 Both services are running!")
            print("Press Ctrl+C to stop all services")
            
            # Monitor processes
            self.monitor_processes()
            
        except KeyboardInterrupt:
            print("\n🛑 Interrupted by user")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
        finally:
            self.shutdown()
            print("👋 Goodbye!")

def check_requirements():
    """
    Check if all required dependencies are installed
    Ensures the application can run properly
    """
    required_packages = {
        'fastapi': 'fastapi',
        'uvicorn': 'uvicorn',
        'streamlit': 'streamlit',
        'langchain': 'langchain',
        'langchain_google_genai': 'langchain-google-genai',
        'langchain_mongodb': 'langchain-mongodb',
        'motor': 'motor',
        'pymongo': 'pymongo',
        'dotenv': 'python-dotenv',
        'requests': 'requests',
        'pydantic': 'pydantic'
    }
    
    missing_packages = []
    
    for import_name, package_name in required_packages.items():
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   • {package}")
        print("\n📦 Install missing packages with:")
        print("pip install " + " ".join(missing_packages))
        return False
    
    return True

def check_environment():
    """
    Check if environment variables are properly set
    Ensures configuration is complete
    """
    required_env_vars = ['GOOGLE_API_KEY', 'MONGODB_URL']
    missing_env_vars = []
    
    for var in required_env_vars:
        if not os.getenv(var):
            missing_env_vars.append(var)
    
    if missing_env_vars:
        print("❌ Missing required environment variables:")
        for var in missing_env_vars:
            print(f"   • {var}")
        print("\n🔧 Please set these in your .env file")
        print("Example .env file:")
        print("GOOGLE_API_KEY=your_google_api_key_here")
        print("MONGODB_URL=mongodb://localhost:27017")
        print("DATABASE_NAME=chat_summarization")
        return False
    
    return True

def main():
    """
    Main entry point for the application launcher
    Performs checks and starts the integrated application
    """
    print("🚀 Chat Summarization API with LangChain MongoDB")
    print("Starting integrated application launcher...")
    print()
    
    # Check requirements
    print("🔍 Checking requirements...")
    if not check_requirements():
        print("❌ Requirements check failed. Please install missing packages.")
        return
    
    print("✅ All packages are installed")
    
    # Check environment
    print("🔍 Checking environment configuration...")
    if not check_environment():
        print("❌ Environment check failed. Please configure environment variables.")
        return
    
    print("✅ Environment configured properly")
    print()
    
    # Start the application
    launcher = AppLauncher()
    launcher.run()

if __name__ == "__main__":
    main()