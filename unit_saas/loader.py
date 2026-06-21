import os
import pandas as pd
import requests
import importlib.util
import sys
from . import prebuilt  

func_registry = {}

def load_functions(module, registry):
    for name in dir(module):
        obj = getattr(module, name)
        if callable(obj):
            registry[name] = obj

# Load prebuilt functions
load_functions(prebuilt, func_registry)

# ---------------------------
# Load user functions dynamically from an external file
# ---------------------------
def load_user_functions(path: str = "user_functions.py"):
    spec = importlib.util.spec_from_file_location("user_functions", path)
    user_module = importlib.util.module_from_spec(spec)
    sys.modules["user_functions"] = user_module
    spec.loader.exec_module(user_module)
    load_functions(user_module, func_registry)

def load_user_functions_from_folder(path: str):
    for filename in os.listdir(path):
        if filename.endswith(".py") and not filename.startswith("__"):
            load_user_functions(os.path.join(path, filename))
       
def loader(security_token: str, gemini_key: str, frame: pd.DataFrame=None,data: dict=None,rules: str=None,address: str="http://localhost:8000/call",vars: list=[]):
    # Create a sample DataFrame

    df = None
    if frame is not None:
        df = frame

    elif data is not None:
        df = pd.DataFrame(data)


    header_row = df.columns.tolist() if df is not None else []

    params = {
        "prompt": rules,
        "function_registry": str(func_registry),
        "header_row": header_row
    }


    headers = {
        "Authorization": f"token {security_token}",
        "x-gemini-api-key": gemini_key
    }

    response = requests.post(url=address,json=params,headers=headers)
    response = response.json()

    # --------------------------
    # Step 2: Execute functions directly
    # --------------------------
    store = {}

    for it in response:
        func_name = it.get('function')
        args = it.get('arguments', {})

    
        # Map dataframe placeholders to actual DataFrame objects
        for key, val in args.items():
            if key == "dataframe":
                if val != 'df':    
                    args[key] = store[val]    

                else:
                    args[key] = df

            if key == "stats":
                    args[key] = store[val] 

    
        # Call the function directly
        try:
            result = func_registry[func_name](**args)
        except Exception as e:
            raise RuntimeError(f"Error executing {func_name} with args {args}: {e}")

        store[func_name] = result
        

    return (list(store.values())[-1],df)      
    
         