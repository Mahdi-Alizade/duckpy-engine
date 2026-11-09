from duckpy.types.dtypes import DuckType
from duckpy.context import DuckPyContext
from duckpy.execution.filter import ComparisonOp


def test_dataframe_inner_join_pipeline():
    ctx = DuckPyContext()

    users_data = [
        [1, "Alice", 101],
        [2, "Bob", 102],
        [3, "Charlie", 999],
    ]
    users_cols = [
        ("user_id", DuckType.INT64),
        ("name", DuckType.STRING),
        ("dept_id", DuckType.INT64),
    ]
    ctx.create_table_from_rows("users", users_cols, users_data, chunk_size=2)

    depts_data = [
        [101, "Engineering", "Building A"],
        [102, "Sales", "Building B"],
    ]
    depts_cols = [
        ("dept_id", DuckType.INT64),
        ("dept_name", DuckType.STRING),
        ("location", DuckType.STRING),
    ]
    ctx.create_table_from_rows("depts", depts_cols, depts_data, chunk_size=2)

    df_users = ctx.table("users")
    df_depts = ctx.table("depts")

    joined_df = (
        df_users.join(df_depts, left_on="dept_id", right_on="dept_id", how="inner")
        .select("name", "dept_name", "location")
    )

    records = joined_df.to_dict()
    assert len(records) == 2
    assert records[0] == {"name": "Alice", "dept_name": "Engineering", "location": "Building A"}
    assert records[1] == {"name": "Bob", "dept_name": "Sales", "location": "Building B"}


def test_dataframe_left_join_with_filter():
    ctx = DuckPyContext()

    orders_data = [
        [10, 500.0, 1],
        [20, 1200.0, 2],
        [30, 300.0, 3],
    ]
    orders_cols = [
        ("order_id", DuckType.INT64),
        ("amount", DuckType.FLOAT64),
        ("cust_id", DuckType.INT64),
    ]
    ctx.create_table_from_rows("orders", orders_cols, orders_data, chunk_size=2)

    customers_data = [
        [1, "VIP Customer"],
    ]
    customers_cols = [
        ("cust_id", DuckType.INT64),
        ("cust_type", DuckType.STRING),
    ]
    ctx.create_table_from_rows("customers", customers_cols, customers_data, chunk_size=2)

    orders_df = ctx.table("orders")
    custs_df = ctx.table("customers")

    joined_df = (
        orders_df.join(custs_df, left_on="cust_id", right_on="cust_id", how="left")
        .filter("amount", ComparisonOp.GREATER_THAN, 400.0)
    )

    records = joined_df.to_dict()
    assert len(records) == 2

    # Order 10 matches VIP Customer
    assert records[0]["order_id"] == 10
    assert records[0]["cust_type"] == "VIP Customer"

    # Order 20 does not match (cust_type is None)
    assert records[1]["order_id"] == 20
    assert records[1]["cust_type"] is None