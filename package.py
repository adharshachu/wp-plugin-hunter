import os
import subprocess
import shutil

def build_frontend():
    print("Building frontend...")
    os.chdir("frontend")
    subprocess.run("npm install", shell=True, check=True)
    subprocess.run("npm run build", shell=True, check=True)
    os.chdir("..")

def create_exe():
    print("Creating EXE...")
    # Bundle FastAPI app + built frontend
    # We use --add-data to include the 'frontend/dist' folder
    # Note: On Windows, the separator is ;
    command = [
        "pyinstaller",
        "--noconfirm",
        "--onefile",
        "--console", # Set to --windowed if you don't want a console
        "--add-data", "frontend/dist;frontend/dist",
        "--add-data", ".env;.",
        "server.py"
    ]
    subprocess.run(" ".join(command), shell=True, check=True)

if __name__ == "__main__":
    try:
        if os.path.exists("frontend"):
            build_frontend()
        create_exe()
        print("\nSuccess! Your EXE is in the 'dist' folder.")
    except Exception as e:
        print(f"\nError during build: {e}")
