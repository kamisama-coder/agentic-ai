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


def loader(security_token: str,frame: pd.DataFrame=None,data: dict=None,rules: str=None,address: str="http://localhost:8000/call",vars: list=[]):
    # Create a sample DataFrame

    df = None
    if frame is not None:
        df = frame

    elif data is not None:
        df = pd.DataFrame(data)


    params = {
    "prompt": rules
}



    headers = {"Authorization": f"token {security_token}"}

    response = requests.post(url=address,json=params,headers=headers)
    response = response.json()

    # --------------------------
    # Step 2: Execute functions directly
    # --------------------------
    store = {}
    dataframes = {
    'df': df 
    }

    for it in response:
        func_name = it.get('function')
        args = it.get('arguments', {})

    
        # Map dataframe placeholders to actual DataFrame objects
        for key, val in args.items():
            if key == "dataframe":
                if val != 'df':    
                    if val not in dataframes:
                        dataframes[val] = list(store.values())[-1]
                        args[key] = dataframes[val]

                    else:    
                        args[key] = dataframes[val]     

                else:
                    args[key] = dataframes[val] 

            if key == "stats":
                if val not in dataframes:
                    dataframes[val] = list(store.values())[-1]
                    args[key] = dataframes[val]

                else:
                    args[key] = dataframes[val]
    


        # Call the function directly
        try:
            result = func_registry[func_name](**args)
        except Exception as e:
            raise RuntimeError(f"Error executing {func_name} with args {args}: {e}")

        store[func_name] = result
        

    if len(vars) != 0:
        return {it: dataframes[it] for it in vars}  # dict of requested outputs
    else:
        return list(store.values())[-1]      
    
    # # 1. Display the head of the DataFrame to inspect it
    # display_head(df, n=3)
    
    # # 2. Plot a line chart of daily sales over time
    # plot_line_chart(df, x_col='date', y_col='daily_sales', title='Daily Sales Trend')

    # # 3. For a bar chart, let's first aggregate the data
    # category_sales = df.groupby('category')['daily_sales'].sum().reset_index()
    # print("\n--- Aggregated Sales by Category ---")
    # print(category_sales)
    
    # # Plot a bar chart of the aggregated sales
    # plot_bar_chart(category_sales, x_col='category', y_col='daily_sales', title='Total Sales by Category')

    # # 4. Save the aggregated data to a CSV file
    # save_dataframe_to_csv(category_sales, 'category_sales_report.csv')        