# TB Generator

## Structure
```
tb_generator/
  app.py
  templates/
    tb.sv.j2
```

## Setup + Run (venv)
```bash
# from the folder containing app.py
python -m venv .venv

# activate:
# mac/linux:
source .venv/bin/activate
# windows powershell:
.\.venv\Scripts\Activate.ps1
# windows cmd:
.\.venv\Scripts\activate.bat

python -m pip install --upgrade pip
pip install streamlit jinja2

streamlit run app.py
```
