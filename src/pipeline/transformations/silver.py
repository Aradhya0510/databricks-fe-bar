"""Silver: typed, validated, de-duplicated business entities. Expectations quarantine the injected source defects."""
from pyspark import pipelines as dp
from pyspark.sql import functions as F, Window

CATALOG = spark.conf.get("osa.catalog")
SCHEMA = spark.conf.get("osa.schema")
FN = f"{CATALOG}.{SCHEMA}"
M5_DAY1 = "2011-01-29"
VALID_STORE = "store_id RLIKE '^(CA_[1-4]|TX_[1-3]|WI_[1-3])$'"


# ---------- reference data ----------

@dp.materialized_view(comment="Calendar dimension (M5): Walmart week, events and state SNAP flags.")
@dp.expect_or_fail("date_present", "date IS NOT NULL")
def silver_calendar():
    return (spark.read.table("bronze_m5_calendar")
            .select(F.to_date("date").alias("date"), F.col("wm_yr_wk").cast("int").alias("wm_yr_wk"),
                    "weekday", F.col("month").cast("int").alias("month"), F.col("year").cast("int").alias("year"),
                    *[F.when(F.col(c) == "NA", None).otherwise(F.col(c)).alias(c)
                      for c in ["event_name_1", "event_type_1", "event_name_2", "event_type_2"]],
                    *[F.col(f"snap_{s}").cast("int").alias(f"snap_{s}") for s in ["CA", "TX", "WI"]])
            .dropDuplicates(["date"]))


@dp.materialized_view(comment="Weekly shelf price per store-item (M5).", cluster_by=["store_id", "item_id"])
@dp.expect_or_drop("positive_price", "sell_price > 0")
def silver_sell_prices():
    return (spark.read.table("bronze_m5_sell_prices")
            .select("store_id", "item_id", F.col("wm_yr_wk").cast("int").alias("wm_yr_wk"),
                    F.col("sell_price").cast("double").alias("sell_price"))
            .dropDuplicates(["store_id", "item_id", "wm_yr_wk"]))


@dp.materialized_view(
    comment="Store dimension (synthetic attributes on the 10 real M5 store ids). Manager e-mails are masked for non-admins.",
    schema=f"""store_id STRING NOT NULL, state_id STRING, region STRING, city STRING, store_name STRING, sqft INT,
               review_weekday INT, store_manager STRING,
               store_manager_email STRING MASK {FN}.fn_mask_email,
               regional_manager_email STRING MASK {FN}.fn_mask_email,
               opened_date DATE, CONSTRAINT dim_store_pk PRIMARY KEY (store_id)""")
def dim_store():
    return (spark.read.table("bronze_erp_stores")
            .select("store_id", "state_id", "region", "city", "store_name", F.col("sqft").cast("int").alias("sqft"),
                    F.col("review_weekday").cast("int").alias("review_weekday"), "store_manager",
                    "store_manager_email", "regional_manager_email", F.to_date("opened_date").alias("opened_date"))
            .dropDuplicates(["store_id"]))


@dp.materialized_view(
    comment="Supplier dimension with contract SLA terms. Commercial terms (penalty, payment terms) are masked "
            "for everyone except osa_sourcing_finance / admins.",
    schema=f"""supplier_id STRING NOT NULL, supplier_name STRING, primary_dept_id STRING, reliability_tier STRING,
               contract_lead_time_days INT, contract_on_time_sla_pct DOUBLE, contract_fill_rate_sla_pct DOUBLE,
               late_penalty_pct_of_po DOUBLE MASK {FN}.fn_mask_commercial_double,
               payment_terms STRING MASK {FN}.fn_mask_commercial_string,
               account_manager_email STRING MASK {FN}.fn_mask_email,
               CONSTRAINT dim_supplier_pk PRIMARY KEY (supplier_id)""")
def dim_supplier():
    return (spark.read.table("bronze_erp_suppliers")
            .select("supplier_id", "supplier_name", "primary_dept_id", "reliability_tier",
                    F.col("contract_lead_time_days").cast("int").alias("contract_lead_time_days"),
                    F.col("contract_on_time_sla_pct").cast("double").alias("contract_on_time_sla_pct"),
                    F.col("contract_fill_rate_sla_pct").cast("double").alias("contract_fill_rate_sla_pct"),
                    F.col("late_penalty_pct_of_po").cast("double").alias("late_penalty_pct_of_po"),
                    "payment_terms", "account_manager_email")
            .dropDuplicates(["supplier_id"]))


@dp.materialized_view(
    comment="Item dimension: M5 item hierarchy + synthetic name, supplier, case pack. Cost ratio is confidential (masked).",
    schema=f"""item_id STRING NOT NULL, item_name STRING, dept_id STRING, cat_id STRING, supplier_id STRING,
               case_pack INT, negotiated_cost_ratio DOUBLE MASK {FN}.fn_mask_commercial_double,
               CONSTRAINT dim_item_pk PRIMARY KEY (item_id)""")
@dp.expect_or_fail("item_has_supplier", "supplier_id IS NOT NULL")
def dim_item():
    return (spark.read.table("bronze_erp_item_master")
            .select("item_id", "item_name", "dept_id", "cat_id", "supplier_id",
                    F.col("case_pack").cast("int").alias("case_pack"),
                    F.col("negotiated_cost_ratio").cast("double").alias("negotiated_cost_ratio"))
            .dropDuplicates(["item_id"]))


# ---------- facts ----------

dp.create_streaming_table(
    name="silver_sales_daily",
    comment="Daily unit sales per store-item. Unpivoted M5 history + live POS feed (append flows).",
    cluster_by=["store_id", "item_id", "date"],
    expect_all_or_drop={"valid_store": VALID_STORE, "item_present": "item_id IS NOT NULL",
                        "non_negative_units": "units >= 0", "date_present": "date IS NOT NULL"},
)


@dp.append_flow(target="silver_sales_daily", name="m5_history_unpivot")
def m5_history_unpivot():
    df = spark.readStream.table("bronze_m5_sales_wide")
    day_cols = [c for c in df.columns if c.startswith("d_")]
    stack = "stack({n}, {pairs}) AS (day_num, units_raw)".format(
        n=len(day_cols), pairs=", ".join(f"{int(c[2:])}, `{c}`" for c in day_cols))
    return (df.select("store_id", "item_id", F.expr(stack), "_source_file")
            .select("store_id", "item_id",
                    F.expr(f"date_add(DATE'{M5_DAY1}', day_num - 1)").alias("date"),
                    F.col("units_raw").cast("int").alias("units"),
                    F.lit("M5_HISTORY").alias("source"), "_source_file"))


@dp.append_flow(target="silver_sales_daily", name="pos_daily_feed")
def pos_daily_feed():
    return (spark.readStream.table("bronze_pos_daily_sales")
            .select("store_id", "item_id", F.col("business_date").alias("date"),
                    F.col("units_sold").cast("int").alias("units"),
                    F.lit("POS_FEED").alias("source"), "_source_file"))


@dp.materialized_view(comment="End-of-day inventory per store-item (validated, de-duplicated).",
                      cluster_by=["store_id", "item_id", "snapshot_date"])
@dp.expect_all_or_drop({"valid_store": VALID_STORE, "item_present": "item_id IS NOT NULL",
                        "non_negative_on_hand": "on_hand_units >= 0", "non_negative_on_order": "on_order_units >= 0"})
def silver_inventory_snapshots():
    return (spark.read.table("bronze_erp_inventory_snapshots")
            .select("store_id", "item_id", "snapshot_date",
                    F.col("on_hand_units").cast("int").alias("on_hand_units"),
                    F.col("on_order_units").cast("int").alias("on_order_units"),
                    F.to_timestamp("extract_ts").alias("extract_ts"))
            .dropDuplicates(["store_id", "item_id", "snapshot_date"]))


@dp.table(comment="Cleansed PO events: event types normalised to upper case, events without quantity dropped.")
@dp.expect_all_or_drop({"po_present": "po_id IS NOT NULL", "qty_present": "qty IS NOT NULL",
                        "known_event": "event_type IN ('CREATED', 'RECEIVED')"})
def silver_po_events():
    return (spark.readStream.table("bronze_erp_po_events")
            .select("po_id", "store_id", "item_id", "supplier_id", F.upper("event_type").alias("event_type"),
                    F.to_date("expected_date").alias("expected_date"), F.col("qty").cast("int").alias("qty"),
                    F.to_timestamp("event_ts").alias("event_ts"), "event_date"))


@dp.materialized_view(comment="One row per purchase order: ordered vs received quantity and dates, lateness, status.",
                      cluster_by=["store_id", "item_id"])
@dp.expect("received_not_before_created", "received_date IS NULL OR received_date >= created_date")
def silver_purchase_orders():
    ev = spark.read.table("silver_po_events")
    created = ev.where("event_type = 'CREATED'").groupBy("po_id").agg(
        F.first("store_id").alias("store_id"), F.first("item_id").alias("item_id"),
        F.first("supplier_id").alias("supplier_id"), F.min("event_date").alias("created_date"),
        F.max("expected_date").alias("expected_date"), F.sum("qty").alias("ordered_qty"))
    received = ev.where("event_type = 'RECEIVED'").groupBy("po_id").agg(
        F.min("event_date").alias("received_date"), F.sum("qty").alias("received_qty"))
    return (created.join(received, "po_id", "left")
            .withColumn("po_type", F.when(F.col("po_id").startswith("DSD-"), "DSD").otherwise("SUPPLIER"))
            .withColumn("status", F.when(F.col("received_date").isNotNull(), "RECEIVED").otherwise("OPEN"))
            .withColumn("days_late", F.when(F.col("received_date").isNotNull(),
                                            F.greatest(F.lit(0), F.datediff("received_date", "expected_date"))))
            .withColumn("on_time", F.col("received_date") <= F.col("expected_date"))
            .withColumn("fill_rate", F.col("received_qty") / F.col("ordered_qty")))
