from unit_saas.loader import loader,load_user_functions
import pandas as pd

if __name__ == "__main__":

    rules =  "Show me total revenue per product and save it in data1 and sort data1 in descending and save it in data2 and then print data2.note:choose the value of dataframe according to you as necessary"

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

    security_token = "8339703acd33444f5b9ea06171519fa5141679d4f722773044b6865c46b3cce1"
    hello_world = loader(data=data,rules=rules,security_token=security_token,address="https://agentic-ai-nt21.onrender.com/call",vars=['data1'])
    print(hello_world)

