cd ~/1_listldr
source ~/1_listldr/venv/bin/activate
# eccho here
pwd
read -r -p "Press Enter to lauch listldr service on port 8000..."
uvicorn api.app:app --reload --host 127.0.0.1 --port 8000
