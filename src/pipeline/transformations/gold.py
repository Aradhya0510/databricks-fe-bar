"""Gold: business-ready facts for analytics, Genie, ML and the app.

Stockout inference (GLOSSARY-OSA-009): a zero-sales day is out-of-stock when it sits in a zero streak of length L
with e^(-lambda*L) < 1%, i.e. lambda*L >= 4.6, lambda >= 0.3 units/day and 2 <= L <= 28, where lambda is the
item-store's trailing 90-day mean daily demand at the start of the streak. Streaks longer than 28 days are treated
as inactive / delisted assortment (excluded from the OSA denominator), not as shelf stockouts.
"""
MAX_OOS_RUN_DAYS = 28
from pyspark import pipelines as dp
from pyspark.sql import functions as F, Window

CATALOG = spark.conf.get("osa.catalog")
SCHEMA = spark.conf.get("osa.schema")
FN = f"{CATALOG}.{SCHEMA}"
REGION_FILTER = f"ROW FILTER {FN}.fn_region_filter ON (region)"

series = Window.partitionBy("store_id", "item_id").orderBy("date")


@dp.materialized_view(
    comment="Store-item-day fact 2011-01-29 onward: units, price, revenue, demand rate, inferred OOS, lost sales, "
            "inventory position (inventory columns populated for the ERP window only).",
    cluster_by=["store_id", "item_id", "date"],
    table_properties={"delta.enableChangeDataFeed": "true"})
@dp.expect("price_known_when_selling", "units = 0 OR sell_price IS NOT NULL")
def gold_store_item_daily():
    sales = spark.read.table("silver_sales_daily").dropDuplicates(["store_id", "item_id", "date"])
    cal = spark.read.table("silver_calendar").select("date", "wm_yr_wk")
    prices = spark.read.table("silver_sell_prices")
    inv = spark.read.table("silver_inventory_snapshots").withColumnRenamed("snapshot_date", "date")
    items = spark.read.table("dim_item").select("item_id", "dept_id", "cat_id", "supplier_id")
    stores = spark.read.table("dim_store").select("store_id", "state_id", "region")

    df = (sales.join(cal, "date", "left")
          .join(prices, ["store_id", "item_id", "wm_yr_wk"], "left")
          .join(inv.select("store_id", "item_id", "date", "on_hand_units", "on_order_units"),
                ["store_id", "item_id", "date"], "left")
          .join(F.broadcast(items), "item_id", "left")
          .join(F.broadcast(stores), "store_id", "left"))

    df = (df.withColumn("lambda_90d", F.avg("units").over(series.rowsBetween(-90, -1)))
            .withColumn("units_prev_7d", F.sum("units").over(series.rowsBetween(-7, -1)))
            .withColumn("nz_grp", F.sum(F.when(F.col("units") > 0, 1).otherwise(0))
                        .over(series.rowsBetween(Window.unboundedPreceding, 0))))
    run = Window.partitionBy("store_id", "item_id", "nz_grp")
    df = (df.withColumn("zero_run_len", F.sum(F.when(F.col("units") == 0, 1).otherwise(0)).over(run))
            .withColumn("zero_run_lambda", F.first(F.when(F.col("units") == 0, F.col("lambda_90d")), ignorenulls=True)
                        .over(run.orderBy("date").rowsBetween(Window.unboundedPreceding, Window.unboundedFollowing))))
    implausible_zero_run = ((F.col("units") == 0) & (F.col("zero_run_lambda") >= 0.3) & (F.col("zero_run_len") >= 2)
                            & (F.col("zero_run_len") * F.col("zero_run_lambda") >= 4.6))
    is_oos = implausible_zero_run & (F.col("zero_run_len") <= MAX_OOS_RUN_DAYS)
    delisted = implausible_zero_run & (F.col("zero_run_len") > MAX_OOS_RUN_DAYS)
    return (df.withColumn("is_oos", F.coalesce(is_oos, F.lit(False)))
              .withColumn("is_active", F.col("is_oos") | ((F.coalesce(F.col("lambda_90d"), F.lit(0)) >= 0.3)
                                                          & ~F.coalesce(delisted, F.lit(False))))
              .withColumn("revenue", F.round(F.col("units") * F.col("sell_price"), 2))
              .withColumn("lost_units", F.when(F.col("is_oos"), F.col("zero_run_lambda")).otherwise(F.lit(0.0)))
              .withColumn("lost_revenue", F.round(F.col("lost_units") * F.coalesce("sell_price", F.lit(0.0)), 2))
              .withColumn("days_of_cover", F.round(F.col("on_hand_units") / F.greatest(F.col("lambda_90d"), F.lit(0.1)), 2))
              .select("date", "wm_yr_wk", "store_id", "state_id", "region", "item_id", "dept_id", "cat_id",
                      "supplier_id", "units", "sell_price", "revenue", F.round("lambda_90d", 3).alias("lambda_90d"),
                      "units_prev_7d", "nz_grp", "is_active", "is_oos", F.round("lost_units", 3).alias("lost_units"),
                      "lost_revenue", "on_hand_units", "on_order_units", "days_of_cover", "source"))


@dp.materialized_view(
    comment="One row per stockout event (maximal run of OOS days) with duration, lost sales and inferred root cause: "
            "SUPPLIER_DELAY, PHANTOM_INVENTORY, DEMAND_SPIKE, UNEXPLAINED, or NO_OPS_DATA (before the ERP window).",
    cluster_by=["store_id", "start_date"], row_filter=REGION_FILTER)
def gold_stockout_events():
    d = spark.read.table("gold_store_item_daily")
    bounds = (spark.read.table("silver_inventory_snapshots").agg(F.min("snapshot_date").alias("ops_start"))
              .crossJoin(d.agg(F.max("date").alias("max_date"))))
    ev = (d.where("is_oos")
          .groupBy("store_id", "item_id", "nz_grp")
          .agg(F.min("date").alias("start_date"), F.max("date").alias("end_date"), F.count("*").alias("oos_days"),
               F.first("state_id").alias("state_id"), F.first("region").alias("region"),
               F.first("dept_id").alias("dept_id"), F.first("cat_id").alias("cat_id"),
               F.first("supplier_id").alias("supplier_id"),
               F.max("lost_units").alias("demand_rate"),
               F.round(F.sum("lost_units"), 2).alias("lost_units"), F.round(F.sum("lost_revenue"), 2).alias("lost_revenue"),
               F.avg("on_hand_units").alias("avg_system_on_hand"),
               F.min_by("units_prev_7d", "date").alias("units_prev_7d")))
    po = (spark.read.table("silver_purchase_orders").where("po_type = 'SUPPLIER'")
          .select("store_id", "item_id", "po_id", "expected_date", "received_date", "days_late"))
    overdue = (ev.join(po, ["store_id", "item_id"])
               .where("expected_date <= start_date AND (received_date IS NULL OR received_date > start_date)")
               .groupBy("store_id", "item_id", "nz_grp")
               .agg(F.first("po_id").alias("overdue_po_id"), F.max("days_late").alias("overdue_po_days_late")))
    ev = ev.join(overdue, ["store_id", "item_id", "nz_grp"], "left").crossJoin(F.broadcast(bounds))
    cause = (F.when(F.col("start_date") < F.col("ops_start"), "NO_OPS_DATA")
              .when(F.col("overdue_po_id").isNotNull(), "SUPPLIER_DELAY")
              .when(F.col("avg_system_on_hand") > 0, "PHANTOM_INVENTORY")
              .when(F.col("units_prev_7d") > 1.5 * 7 * F.col("demand_rate"), "DEMAND_SPIKE")
              .otherwise("UNEXPLAINED"))
    return (ev.withColumn("root_cause", cause)
              .withColumn("is_ongoing", F.col("end_date") == F.col("max_date"))
              .withColumn("event_id", F.concat_ws("|", "store_id", "item_id", F.col("start_date").cast("string")))
              .select("event_id", "store_id", "state_id", "region", "item_id", "dept_id", "cat_id", "supplier_id",
                      "start_date", "end_date", "oos_days", "is_ongoing", F.round("demand_rate", 3).alias("demand_rate"),
                      "lost_units", "lost_revenue", "root_cause", "overdue_po_id", "overdue_po_days_late",
                      F.round("avg_system_on_hand", 1).alias("avg_system_on_hand")))


@dp.materialized_view(
    comment="Daily OSA KPI by store x department: active store-items, OOS store-items, OSA %, revenue, lost revenue. "
            "Row-filtered by region.",
    cluster_by=["date", "store_id"], row_filter=REGION_FILTER)
def gold_osa_kpi_daily():
    d = spark.read.table("gold_store_item_daily")
    return (d.groupBy("date", "store_id", "state_id", "region", "dept_id", "cat_id")
            .agg(F.sum(F.col("is_active").cast("int")).alias("active_store_items"),
                 F.sum(F.col("is_oos").cast("int")).alias("oos_store_items"),
                 F.sum("units").alias("units"), F.round(F.sum("revenue"), 2).alias("revenue"),
                 F.round(F.sum("lost_units"), 1).alias("lost_units"), F.round(F.sum("lost_revenue"), 2).alias("lost_revenue"))
            .withColumn("osa_pct", F.round(100 * (1 - F.col("oos_store_items") / F.greatest("active_store_items", F.lit(1))), 2))
            .withColumn("lost_sales_rate_pct",
                        F.round(100 * F.col("lost_revenue") / F.greatest(F.col("revenue") + F.col("lost_revenue"), F.lit(0.01)), 2)))


@dp.materialized_view(
    comment="Supplier scorecard by Walmart week of PO due date: on-time %, days late, fill rate, attributed stockouts "
            "and lost revenue.",
    cluster_by=["supplier_id"])
def gold_supplier_performance_weekly():
    cal = spark.read.table("silver_calendar").select("date", "wm_yr_wk")
    po = (spark.read.table("silver_purchase_orders").where("po_type = 'SUPPLIER' AND status = 'RECEIVED'")
          .join(cal.withColumnRenamed("date", "expected_date"), "expected_date"))
    perf = (po.groupBy("supplier_id", "wm_yr_wk")
            .agg(F.min("expected_date").alias("week_start"), F.count("*").alias("pos_received"),
                 F.round(100 * F.avg(F.col("on_time").cast("int")), 2).alias("on_time_pct"),
                 F.round(F.avg("days_late"), 2).alias("avg_days_late"),
                 F.round(100 * F.sum("received_qty") / F.sum("ordered_qty"), 2).alias("fill_rate_pct")))
    ev = (spark.read.table("gold_stockout_events").where("root_cause = 'SUPPLIER_DELAY'")
          .join(cal.withColumnRenamed("date", "start_date"), "start_date")
          .groupBy("supplier_id", "wm_yr_wk")
          .agg(F.count("*").alias("attributed_stockouts"), F.round(F.sum("lost_revenue"), 2).alias("attributed_lost_revenue")))
    sup = spark.read.table("dim_supplier").select("supplier_id", "supplier_name", "reliability_tier",
                                                  "contract_on_time_sla_pct", "contract_fill_rate_sla_pct")
    return (perf.join(ev, ["supplier_id", "wm_yr_wk"], "left").join(sup, "supplier_id", "left")
            .fillna({"attributed_stockouts": 0, "attributed_lost_revenue": 0.0})
            .withColumn("meets_on_time_sla", F.col("on_time_pct") >= F.col("contract_on_time_sla_pct")))
