import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))) 

import uvicorn
from app import app

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
    
    
