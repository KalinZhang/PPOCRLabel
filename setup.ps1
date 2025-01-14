Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
.\venv-win\Scripts\activate.ps1
python -m ensurepip
python -m pip install --upgrade pip
python -m pip install paddlepaddle pyqt5 paddleocr openpyxl tqdm premailer pandas requests
python PPOCRLabel.py