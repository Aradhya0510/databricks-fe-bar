"""ML feature table for the 3-day stockout-risk model.

Grain: store-item-day over the ERP window (end-of-day state). All features use information available at the end of
day t; the label looks forward t+1..t+3 and is NULL where the future is not yet observed (i.e. the scoring rows).
"""
from pyspark import pipelines as dp
from pyspark.sql import functions as F, Window

series = Window.partitionBy("store_id", "item_id").orderBy("date")


@dp.temporary_view()
def calendar_lookahead():
    cal = spark.read.table("silver_calendar")
    ahead = Window.orderBy("date").rowsBetween(1, 3)
    out = cal.withColumn("has_event", F.col("event_name_1").isNotNull().cast("int"))
    for s in ["CA", "TX", "WI"]:
        out = out.withColumn(f"snap_next3_{s}", F.max(f"snap_{s}").over(ahead))
    return (out.withColumn("event_next3", F.max("has_event").over(ahead))
               .withColumn("dow", F.dayofweek("date"))
               .select("date", "dow", "event_next3", "snap_next3_CA", "snap_next3_TX", "snap_next3_WI"))


@dp.temporary_view()
def open_po_daily():
    """Open supplier/DSD POs per store-item-day (created on/before t, not yet received at end of t)."""
    days = (spark.read.table("silver_inventory_snapshots")
            .select("store_id", "item_id", F.col("snapshot_date").alias("date")))
    po = spark.read.table("silver_purchase_orders").select(
        "store_id", "item_id", "created_date", "expected_date", "received_date", "ordered_qty")
    j = days.join(po, ["store_id", "item_id"]).where(
        "created_date <= date AND (received_date IS NULL OR received_date > date)")
    return (j.groupBy("store_id", "item_id", "date")
            .agg(F.count("*").alias("open_po_count"),
                 F.sum("ordered_qty").alias("open_po_qty"),
                 F.sum(F.when(F.col("expected_date") <= F.col("date"), 1).otherwise(0)).alias("overdue_po_count"),
                 F.max(F.when(F.col("expected_date") <= F.col("date"), F.datediff("date", "expected_date"))).alias("max_days_overdue"),
                 F.min(F.when(F.col("expected_date") > F.col("date"), F.datediff("expected_date", "date"))).alias("days_to_next_receipt")))


@dp.temporary_view()
def supplier_on_time_trailing():
    """Supplier on-time rate over POs due in the previous 56 days, for every day in the ERP window."""
    po = spark.read.table("silver_purchase_orders").where("po_type = 'SUPPLIER' AND status = 'RECEIVED'")
    daily = (po.groupBy("supplier_id", F.col("expected_date").alias("date"))
             .agg(F.count("*").alias("n"), F.sum(F.col("on_time").cast("int")).alias("n_on_time")))
    grid = (spark.read.table("dim_supplier").select("supplier_id")
            .crossJoin(spark.read.table("silver_inventory_snapshots").select(F.col("snapshot_date").alias("date")).distinct()))
    g = grid.join(daily, ["supplier_id", "date"], "left").fillna({"n": 0, "n_on_time": 0}) \
            .withColumn("dnum", F.datediff("date", F.lit("2000-01-01")))
    w = Window.partitionBy("supplier_id").orderBy("dnum").rangeBetween(-56, -1)
    return (g.withColumn("sup_on_time_56d", F.sum("n_on_time").over(w) / F.greatest(F.sum("n").over(w), F.lit(1)))
             .select("supplier_id", "date", F.round("sup_on_time_56d", 4).alias("sup_on_time_56d")))


@dp.materialized_view(
    comment="Daily feature vector + 3-day-ahead stockout label per store-item over the ERP window. "
            "label_oos_next3 is NULL for the most recent days (scoring rows).",
    cluster_by=["date", "store_id"])
@dp.expect("cover_known", "days_of_cover IS NOT NULL")
def gold_stockout_features():
    d = (spark.read.table("gold_store_item_daily")
         .select("date", "store_id", "state_id", "region", "item_id", "dept_id", "cat_id", "supplier_id", "units",
                 "sell_price", "lambda_90d", "is_oos", "lost_revenue", "on_hand_units", "on_order_units",
                 "days_of_cover"))
    d = (d.withColumn("avg_units_7d", F.avg("units").over(series.rowsBetween(-6, 0)))
          .withColumn("avg_units_28d", F.avg("units").over(series.rowsBetween(-27, 0)))
          .withColumn("std_units_28d", F.stddev("units").over(series.rowsBetween(-27, 0)))
          .withColumn("last_sale_date", F.last(F.when(F.col("units") > 0, F.col("date")), ignorenulls=True)
                      .over(series.rowsBetween(Window.unboundedPreceding, 0)))
          .withColumn("price_7d_ago", F.lag("sell_price", 7).over(series))
          .withColumn("label_oos_next3", F.max(F.col("is_oos").cast("int")).over(series.rowsBetween(1, 3)))
          .withColumn("lost_revenue_next3", F.sum("lost_revenue").over(series.rowsBetween(1, 3)))
          .withColumn("future_rows", F.count("*").over(series.rowsBetween(1, 3)))
          .where("on_hand_units IS NOT NULL"))
    sup = spark.read.table("dim_supplier").select("supplier_id", "reliability_tier", "contract_lead_time_days")
    feat = (d.join(spark.read.table("open_po_daily"), ["store_id", "item_id", "date"], "left")
             .join(spark.read.table("supplier_on_time_trailing"), ["supplier_id", "date"], "left")
             .join(F.broadcast(spark.read.table("calendar_lookahead")), "date", "left")
             .join(F.broadcast(sup), "supplier_id", "left")
             .fillna({"open_po_count": 0, "open_po_qty": 0, "overdue_po_count": 0}))
    lam = F.greatest(F.col("lambda_90d"), F.lit(0.1))
    streak = F.datediff("date", "last_sale_date")
    oos_so_far = F.coalesce((F.col("units") == 0) & (F.col("lambda_90d") >= 0.3) & (streak >= 2) & (streak <= 28)
                            & (streak * F.col("lambda_90d") >= 4.6), F.lit(False))
    return feat.select(
        "date", "store_id", "state_id", "region", "item_id", "dept_id", "cat_id", "supplier_id", "reliability_tier",
        "contract_lead_time_days", "units", "sell_price", F.round("lambda_90d", 3).alias("lambda_90d"),
        F.round("avg_units_7d", 3).alias("avg_units_7d"), F.round("avg_units_28d", 3).alias("avg_units_28d"),
        F.round(F.col("std_units_28d") / F.greatest(F.col("avg_units_28d"), F.lit(0.1)), 3).alias("cv_units_28d"),
        F.round(F.col("avg_units_7d") / F.greatest(F.col("avg_units_28d"), F.lit(0.1)), 3).alias("trend_7_28"),
        F.coalesce(F.datediff("date", "last_sale_date"), F.lit(999)).alias("days_since_last_sale"),
        F.round(F.coalesce(F.col("sell_price") / F.col("price_7d_ago") - 1, F.lit(0.0)), 4).alias("price_change_7d"),
        "on_hand_units", "on_order_units", "days_of_cover",
        F.round((F.col("on_hand_units") + F.col("on_order_units")) / lam, 2).alias("position_cover_days"),
        "open_po_count", "open_po_qty", "overdue_po_count", F.coalesce("max_days_overdue", F.lit(-1)).alias("max_days_overdue"),
        F.coalesce("days_to_next_receipt", F.lit(99)).alias("days_to_next_receipt"),
        F.coalesce("sup_on_time_56d", F.lit(0.95)).alias("sup_on_time_56d"),
        "dow", F.coalesce("event_next3", F.lit(0)).alias("event_next3"),
        F.coalesce(F.when(F.col("state_id") == "CA", F.col("snap_next3_CA"))
                    .when(F.col("state_id") == "TX", F.col("snap_next3_TX"))
                    .otherwise(F.col("snap_next3_WI")), F.lit(0)).alias("snap_next3"),
        # causal OOS-so-far: uses only the zero streak observed up to end of day t (no look-ahead)
        oos_so_far.alias("is_oos_today"),
        (oos_so_far & (F.col("on_hand_units") > 0)).alias("suspected_phantom"),
        F.when(F.col("future_rows") == 3, F.col("label_oos_next3")).alias("label_oos_next3"),
        F.when(F.col("future_rows") == 3, F.round("lost_revenue_next3", 2)).alias("lost_revenue_next3"))
