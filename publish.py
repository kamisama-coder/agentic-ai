from unit_saas import loader

if __name__ == "__main__":

    rules =  """Take the DataFrame df and perform the following steps:

1. Display the first 5 rows of df.

2. Handle any missing values in the column 'Age' by filling them with the mean of the column, storing the updated DataFrame in a variable called 'df_filled'.

3. Remove any duplicate rows from 'df_filled', storing the result in 'df_no_duplicates'.

4. Change the data type of the column 'Age' in 'df_no_duplicates' to integer, storing the result in 'df_typed'.

5. Filter 'df_typed' to include only rows where 'Is_Student' is True, storing the result in 'df_students'.

6. Calculate descriptive statistics (mean, median, std, min, max, count) for the 'Age' column in 'df_students' and store the result in a variable called 'student_age_stats'.

7. Display the contents of 'student_age_stats' with the title "Student Age Statistics".
"""

    data = {
    'Name': ['Alice', 'Bob', 'Charlie', 'David'],
    'Age': [25, 30, 28, 22],
    'City': ['New York', 'London', 'Paris', 'Tokyo'],
    'Is_Student': [True, False, False, True]
    }

    security_token = "089f9d1475e3db7fd6ecc8a218ebd974b40f0b3fcf3d88bc6b6c9b8b6d55444c"

    loader(data=data,rules=rules,security_token=security_token)

