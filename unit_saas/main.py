import pandas as pd
import boto3
from sqlalchemy import create_engine, text
from botocore.exceptions import NoCredentialsError, ClientError
import numpy as np
import matplotlib.pyplot as plt
import importlib.util
import requests


def run_sql_query(connection_string: str, query: str) -> pd.DataFrame:
    """
    Executes a SQL query against a database and returns the result as a Pandas DataFrame.
    The connection_string should be a valid SQLAlchemy connection string.
    
    Example connection_string for PostgreSQL:
    'postgresql://user:password@host:port/database'
    """
    try:
        # Create a SQLAlchemy engine to connect to the database
        engine = create_engine(connection_string)
        
        # Use a context manager to ensure the connection is closed
        with engine.connect() as connection:
            # Use pandas to directly read the SQL query into a DataFrame
            dataframe = pd.read_sql_query(sql=text(query), con=connection)
        
        print("✅ SQL query executed successfully.")
        return dataframe

    except Exception as e:
        print(f"❌ Error executing SQL query: {e}")
        # Return an empty DataFrame in case of an error
        return pd.DataFrame()


def load_csv_from_s3(bucket: str, key: str, separator: str = ',') -> pd.DataFrame:
    """
    Loads a CSV file from an AWS S3 bucket into a Pandas DataFrame.
    'key' is the full path to the file within the bucket.
    
    Assumes AWS credentials are configured (e.g., via environment variables, IAM role).
    """
    try:
        # Create an S3 client
        s3_client = boto3.client('s3')
        
        # Get the object from S3
        response = s3_client.get_object(Bucket=bucket, Key=key)
        
        # Read the object's body directly into a pandas DataFrame
        dataframe = pd.read_csv(response.get("Body"), sep=separator)
        
        print(f"✅ Successfully loaded '{key}' from bucket '{bucket}'.")
        return dataframe
        
    except NoCredentialsError:
        print("❌ AWS credentials not found. Please configure them.")
        return pd.DataFrame()
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            print(f"❌ The file '{key}' does not exist in bucket '{bucket}'.")
        else:
            print(f"❌ An unexpected AWS error occurred: {e}")
        return pd.DataFrame()
    except Exception as e:
        print(f"❌ An error occurred while loading the CSV: {e}")
        return pd.DataFrame()
    
# Data Cleaning & Preprocessing Functions
def handle_missing_values(dataframe: pd.DataFrame, column: str, strategy: str, fill_value=None) -> pd.DataFrame:
    """
    Handles missing (NaN) values in a specific column of a DataFrame.
    Supported strategies are: 'drop' (removes rows), 'fill' (uses fill_value), 'mean', 'median'.
    """
    df = dataframe.copy()

    if column not in df.columns:
        print(f"❌ Error: Column '{column}' not found in the DataFrame.")
        return dataframe # Return original dataframe

    if strategy == 'drop':
        df.dropna(subset=[column], inplace=True)
    elif strategy == 'fill':
        if fill_value is None:
            print("❌ Error: 'fill' strategy requires a 'fill_value'.")
            return dataframe
        df[column].fillna(fill_value, inplace=True)
    elif strategy in ['mean', 'median']:
        if pd.api.types.is_numeric_dtype(df[column]):
            if strategy == 'mean':
                fill_val = df[column].mean()
            else: # median
                fill_val = df[column].median()
            df[column].fillna(fill_val, inplace=True)
        else:
            print(f"❌ Error: Cannot calculate '{strategy}' for non-numeric column '{column}'.")
            return dataframe
    else:
        print(f"❌ Error: Invalid strategy '{strategy}'. Supported strategies are 'drop', 'fill', 'mean', 'median'.")
        return dataframe
    
    print(f"✅ Handled missing values in '{column}' using strategy '{strategy}'.")
    return df

def remove_duplicates(dataframe: pd.DataFrame) -> pd.DataFrame:
    """
    Removes duplicate rows from the entire DataFrame.
    """
    df = dataframe.copy()
    initial_rows = len(df)
    df.drop_duplicates(inplace=True)
    rows_removed = initial_rows - len(df)
    print(f"✅ Removed {rows_removed} duplicate row(s).")
    return df

def change_column_type(dataframe: pd.DataFrame, column: str, new_type: str) -> pd.DataFrame:
    """
    Changes the data type of a specified column.
    Supported new_types: 'integer', 'float', 'string', 'datetime'.
    """
    df = dataframe.copy()

    if column not in df.columns:
        print(f"❌ Error: Column '{column}' not found.")
        return dataframe

    type_map = {
        'integer': 'Int64', # Using nullable integer type
        'float': 'float64',
        'string': 'str'
    }

    try:
        if new_type == 'datetime':
            df[column] = pd.to_datetime(df[column])
        elif new_type in type_map:
            df[column] = df[column].astype(type_map[new_type])
        else:
            print(f"❌ Error: Unsupported type '{new_type}'.")
            return dataframe
        
        print(f"✅ Changed column '{column}' to type '{new_type}'.")
        return df
    except Exception as e:
        print(f"❌ Error converting column '{column}' to type '{new_type}': {e}")
        return dataframe

def rename_columns(dataframe: pd.DataFrame, rename_map: dict) -> pd.DataFrame:
    """
    Renames one or more columns in the DataFrame.
    The rename_map should be a dictionary like {'old_name_1': 'new_name_1', 'old_name_2': 'new_name_2'}.
    """
    df = dataframe.copy()
    
    if not isinstance(rename_map, dict):
        print("❌ Error: 'rename_map' must be a dictionary.")
        return dataframe
    
    df.rename(columns=rename_map, inplace=True)
    print(f"✅ Renamed columns: {list(rename_map.keys())}.")
    return df    

def filter_rows(dataframe: pd.DataFrame, column: str, operator: str, value) -> pd.DataFrame:
    """
    Filters rows in a DataFrame based on a condition.
    Supported operators: '==', '!=', '>', '<', '>=', '<=', 'contains'.
    'value' is the value to compare against. For 'contains', value must be a string.
    """
    df = dataframe.copy()

    if column not in df.columns:
        print(f"❌ Error: Column '{column}' not found in the DataFrame.")
        return dataframe

    try:
        if operator == '==':
            result_df = df[df[column] == value]
        elif operator == '!=':
            result_df = df[df[column] != value]
        elif operator == '>':
            result_df = df[df[column] > value]
        elif operator == '<':
            result_df = df[df[column] < value]
        elif operator == '>=':
            result_df = df[df[column] >= value]
        elif operator == '<=':
            result_df = df[df[column] <= value]
        elif operator == 'contains':
            if not isinstance(value, str):
                print("❌ Error: 'contains' operator requires a string value.")
                return dataframe
            result_df = df[df[column].str.contains(value, na=False)]
        else:
            print(f"❌ Error: Invalid operator '{operator}'.")
            return dataframe
            
        print(f"✅ Filtered rows where '{column}' {operator} '{value}'.")
        return result_df
    except TypeError:
        print(f"❌ Error: The data in column '{column}' is not compatible with the operator '{operator}'. Please check the column's data type.")
        return dataframe

def select_columns(dataframe: pd.DataFrame, columns_to_keep: list) -> pd.DataFrame:
    """
    Selects a subset of columns from a DataFrame, discarding the rest.
    columns_to_keep is a list of column names.
    """
    if not isinstance(columns_to_keep, list):
        print("❌ Error: 'columns_to_keep' must be a list.")
        return dataframe
    
    # Check if all columns to keep exist in the dataframe
    missing_cols = [col for col in columns_to_keep if col not in dataframe.columns]
    if missing_cols:
        print(f"❌ Error: The following columns were not found: {missing_cols}")
        return dataframe
    
    print(f"✅ Selected columns: {columns_to_keep}.")
    return dataframe[columns_to_keep].copy()

def join_dataframes(df1: pd.DataFrame, df2: pd.DataFrame, on_column: str, how: str = 'inner') -> pd.DataFrame:
    """
    Joins two DataFrames together based on a common column.
    Supported 'how' methods: 'inner', 'left', 'right', 'outer'.
    """
    if on_column not in df1.columns or on_column not in df2.columns:
        print(f"❌ Error: Join column '{on_column}' not found in both DataFrames.")
        return pd.DataFrame() # Return an empty DataFrame

    supported_joins = ['inner', 'left', 'right', 'outer']
    if how not in supported_joins:
        print(f"❌ Error: Invalid join method '{how}'. Supported methods are: {supported_joins}.")
        return pd.DataFrame()
    
    try:
        merged_df = pd.merge(df1, df2, on=on_column, how=how)
        print(f"✅ Successfully joined DataFrames on '{on_column}' using a '{how}' join.")
        return merged_df
    except Exception as e:
        print(f"❌ An error occurred during the join operation: {e}")
        return pd.DataFrame()
    
def group_by_aggregate(dataframe: pd.DataFrame, group_by_col: str, agg_col: str, agg_func: str) -> pd.DataFrame:
    """
    Groups a DataFrame by a column and performs an aggregation on another column.
    Supported agg_func: 'sum', 'mean', 'count', 'std' (standard deviation), 'min', 'max'.
    Returns a new DataFrame with the grouped and aggregated results.
    """
    if group_by_col not in dataframe.columns or agg_col not in dataframe.columns:
        print(f"❌ Error: One or both columns ('{group_by_col}', '{agg_col}') not found.")
        return pd.DataFrame()

    supported_funcs = ['sum', 'mean', 'count', 'std', 'min', 'max']
    if agg_func not in supported_funcs:
        print(f"❌ Error: Invalid aggregation function '{agg_func}'. Supported functions are: {supported_funcs}.")
        return pd.DataFrame()

    # Mean, std, sum, min, max require a numeric aggregation column
    if agg_func != 'count' and not pd.api.types.is_numeric_dtype(dataframe[agg_col]):
        print(f"❌ Error: Aggregation function '{agg_func}' requires a numeric column for '{agg_col}'.")
        return pd.DataFrame()
        
    try:
        print(f"✅ Grouping by '{group_by_col}' and aggregating '{agg_col}' with '{agg_func}'.")
        # Group, aggregate, and then reset the index to turn the result back into a DataFrame
        result_df = dataframe.groupby(group_by_col)[agg_col].agg(agg_func).reset_index()
        return result_df
    except Exception as e:
        print(f"❌ An error occurred during aggregation: {e}")
        return pd.DataFrame()


def sort_values(dataframe: pd.DataFrame, by_column: str, ascending: bool = False) -> pd.DataFrame:
    """
    Sorts the DataFrame by the values in a specified column.
    """
    if by_column not in dataframe.columns:
        print(f"❌ Error: Column '{by_column}' not found for sorting.")
        return dataframe
    
    print(f"✅ Sorting DataFrame by '{by_column}' in {'ascending' if ascending else 'descending'} order.")
    # sort_values returns a new DataFrame by default
    return dataframe.sort_values(by=by_column, ascending=ascending)


def get_descriptive_statistics(dataframe: pd.DataFrame, column: str) -> dict:
    """
    Calculates descriptive statistics for a numerical column.
    Returns a dictionary with metrics like mean, median, std, min, max, and count.
    """
    if column not in dataframe.columns:
        print(f"❌ Error: Column '{column}' not found.")
        return {}

    if not pd.api.types.is_numeric_dtype(dataframe[column]):
        print(f"❌ Error: Descriptive statistics can only be calculated for numeric columns. '{column}' is not numeric.")
        return {}
    
    print(f"✅ Calculating descriptive statistics for '{column}'.")
    # .describe() returns a pandas Series, .to_dict() converts it to a dictionary
    return dataframe[column].describe().to_dict()

def display_stats(stats: dict, title: str = "Descriptive Statistics"):
    """
    Displays the contents of a descriptive statistics dictionary in a readable format.
    
    Args:
        stats (dict): Dictionary containing descriptive statistics.
        title (str): Optional title to display above the stats.
    """
    if not stats:
        print("❌ No statistics to display.")
        return
    
    print(f"--- {title} ---")
    for key, value in stats.items():
        print(f"{key}: {value}")
    print("--------------------")


def display_head(dataframe: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """
    Displays the first N rows of the DataFrame. Useful for inspecting the data at any step.
    This function should be called frequently by the AI for sanity checks.
    """
    print(f"--- Displaying first {n} rows ---")
    print(dataframe.head(n))
    # Return the original DataFrame to allow for further chaining
    return dataframe

def plot_bar_chart(dataframe: pd.DataFrame, x_col: str, y_col: str, title: str):
    """
    Generates and displays a bar chart from the DataFrame.
    """
    if x_col not in dataframe.columns or y_col not in dataframe.columns:
        print(f"❌ Error: One or both columns ('{x_col}', '{y_col}') not found for plotting.")
        return

    try:
        print(f"📊 Displaying bar chart: '{title}'... (Close the plot window to continue)")
        plt.figure(figsize=(10, 6)) # Create a figure with a nice size
        plt.bar(dataframe[x_col], dataframe[y_col])
        plt.xlabel(x_col)
        plt.ylabel(y_col)
        plt.title(title)
        plt.xticks(rotation=45, ha='right') # Rotate x-axis labels for readability
        plt.tight_layout() # Adjust layout to make room for labels
        plt.show() # This opens the plot window
    except Exception as e:
        print(f"❌ An error occurred while plotting: {e}")


def plot_line_chart(dataframe: pd.DataFrame, x_col: str, y_col: str, title: str):
    """
    Generates and displays a line chart from the DataFrame. Ideal for time-series data.
    """
    if x_col not in dataframe.columns or y_col not in dataframe.columns:
        print(f"❌ Error: One or both columns ('{x_col}', '{y_col}') not found for plotting.")
        return
        
    try:
        print(f"📈 Displaying line chart: '{title}'... (Close the plot window to continue)")
        plt.figure(figsize=(10, 6))
        plt.plot(dataframe[x_col], dataframe[y_col], marker='o') # Add markers for data points
        plt.xlabel(x_col)
        plt.ylabel(y_col)
        plt.title(title)
        plt.grid(True) # Add a grid for better readability
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.show()
    except Exception as e:
        print(f"❌ An error occurred while plotting: {e}")


def save_dataframe_to_csv(dataframe: pd.DataFrame, filename: str):
    """
    Saves the final DataFrame to a local CSV file.
    """
    try:
        # index=False is important to avoid writing the DataFrame index as a column
        dataframe.to_csv(filename, index=False)
        print(f"✅ Successfully saved DataFrame to '{filename}'.")
    except Exception as e:
        print(f"❌ An error occurred while saving the file: {e}")    


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
    print("LLM Response:", response)


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
            result = globals()[func_name](**args)
        except Exception as e:
            raise RuntimeError(f"Error executing {func_name} with args {args}: {e}")

        store[func_name] = result
        

    if len(vars) != 0:
        return {it: store[it] for it in vars}  # dict of requested outputs
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