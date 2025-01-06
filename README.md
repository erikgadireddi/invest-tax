Czech tax optimizer using streamlit as its web UX.

# Installation:

```
pip install -r requirements.txt
streamlit app.py
```
The one-time pip installation need to happen as administrator so it adds streamlit.exe to your path. 
Alternatively, you can run it using its absolute path.

# Usage:
Export Interactive Brokers Statements->**Activity Statements** and drop them into its UX. IBKR allows you to export only up to a year worth of data, so you might need to do multiple exports to cover all your trading (overlapping timeframes are fully supported). Good strategy is to first export 'Year to Date' and then continue with 'Annual' for all years you can select.

Report all problems here!
