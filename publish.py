from unit_saas.loader import loader,load_user_functions
import pandas as pd

if __name__ == "__main__":

    rules =  "Show me the total revenue for each product, sorted from highest to lowest"

    data = {
    "orderID": [1001, 1002, 1003, 1004, 1005, 1006, 1007],
    "customerID": [501, 502, 503, 501, 504, 505, 502],
    "customerName": ["Alice", "Bob", "Charlie", "Alice", "David", "Eve", "Bob"],
    "product": ["Laptop", "Phone", "Tablet", "Laptop", "Monitor", "Phone", "Tablet"],
    "Category": ["Electronics", "Electronics", "Electronics", "Electronics", "Electronics", "Electronics", "Electronics"],
    "units": [2, 5, 3, 1, 4, 2, 1],
    "unitPrice": [1200, 500, 300, 1200, 250, 500, 300],
    "revenue": [2400, 2500, 900, 1200, 1000, 1000, 300],
    "orderDate": pd.to_datetime([
        "2025-01-01", "2025-01-02", "2025-01-03",
        "2025-01-05", "2025-01-07", "2025-01-08", "2025-01-09"
    ]),
    "region": ["North", "South", "East", "North", "West", "South", "South"]
}

    security_token = "1ed338390119fa9eb9c24c602fa883c2ef435e14e409fbb2dd4865a73ad6d0e5"
    hello_world = loader(data=data,rules=rules,security_token=security_token,gemini_key="AIzaSyBtXExmhI5vjn1ZxvfN-2fTDdO4IzkWRPE")
    print(hello_world)

