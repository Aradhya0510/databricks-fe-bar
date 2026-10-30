"""Bronze: raw files from the landing volume, ingested incrementally with Auto Loader (as-is, plus lineage columns)."""
from pyspark import pipelines as dp
from pyspark.sql import functions as F

RAW = spark.conf.get("osa.raw_path")


def autoload(path, fmt, schema=None, partition_col=None):
    reader = spark.readStream.format("cloudFiles").option("cloudFiles.format", fmt)
    if fmt == "csv":
        reader = reader.option("header", "true")
    if partition_col:
        reader = reader.option("cloudFiles.partitionColumns", partition_col)
    if schema:
        reader = reader.schema(schema)
    return (reader.load(f"{RAW}/{path}")
            .withColumn("_source_file", F.col("_metadata.file_path"))
            .withColumn("_ingested_at", F.current_timestamp()))


# ---------- public M5 dataset (unchanged competition files) ----------

@dp.table(comment="M5 calendar.csv as published: dates, Walmart week, events, SNAP flags per state.",
          table_properties={"source": "public:m5"})
def bronze_m5_calendar():
    return autoload("m5/calendar", "csv")


@dp.table(comment="M5 sell_prices.csv as published: weekly shelf price per store-item.",
          table_properties={"source": "public:m5"})
def bronze_m5_sell_prices():
    return autoload("m5/sell_prices", "csv")


@dp.table(comment="M5 sales_train_evaluation.csv as published: one row per store-item, one column per day (d_1..d_1941).",
          table_properties={"source": "public:m5"})
def bronze_m5_sales_wide():
    return autoload("m5/sales_history", "csv")


@dp.table(comment="Daily POS sales feed (store-item-day units). Replays the real M5 evaluation period after the as-of date.",
          table_properties={"source": "public:m5"})
def bronze_pos_daily_sales():
    return autoload("pos/daily_sales", "csv",
                    schema="store_id STRING, item_id STRING, units_sold STRING, business_date DATE, _rescued_data STRING",
                    partition_col="business_date")


# ---------- simulated ERP / WMS extracts ----------

@dp.table(comment="ERP store master extract (synthetic).", table_properties={"source": "synthetic"})
def bronze_erp_stores():
    return autoload("erp/stores", "csv")


@dp.table(comment="ERP supplier master extract incl. contract terms (synthetic).", table_properties={"source": "synthetic"})
def bronze_erp_suppliers():
    return autoload("erp/suppliers", "csv")


@dp.table(comment="ERP item master: item -> supplier, negotiated cost ratio, case pack (synthetic).",
          table_properties={"source": "synthetic"})
def bronze_erp_item_master():
    return autoload("erp/item_master", "csv")


@dp.table(comment="WMS end-of-day inventory snapshots, one folder per day (synthetic, aligned to M5 demand).",
          table_properties={"source": "synthetic"})
def bronze_erp_inventory_snapshots():
    return autoload("erp/inventory_snapshots", "csv",
                    schema=("store_id STRING, item_id STRING, on_hand_units STRING, on_order_units STRING, "
                            "extract_ts STRING, snapshot_date DATE, _rescued_data STRING"),
                    partition_col="snapshot_date")


@dp.table(comment="ERP purchase-order lifecycle events (CREATED / RECEIVED), JSON lines, one folder per day (synthetic).",
          table_properties={"source": "synthetic"})
def bronze_erp_po_events():
    return autoload("erp/po_events", "json",
                    schema=("po_id STRING, store_id STRING, item_id STRING, supplier_id STRING, event_type STRING, "
                            "expected_date STRING, qty BIGINT, event_ts STRING, event_date DATE, _rescued_data STRING"),
                    partition_col="event_date")
