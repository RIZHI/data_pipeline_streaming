from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, window, lit, expr
from pyspark.sql.types import StructType, StringType, LongType, DoubleType
from pyspark.sql import SparkSession

# Define schema for incoming Kafka JSON value
schema = StructType() \
    .add("asset_id", StringType()) \
    .add("timestamp", LongType()) \
    .add("status", DoubleType())  # status: 0, 1, 2, 408


packages = ["org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.3"]

spark = SparkSession.builder \
    .appName("MachineDataAggregator") \
    .master("local[1]") \
    .config("spark.ui.enabled", "true") \
    .config("spark.ui.port", "4040") \
    .config("spark.executor.memory", "1g") \
    .config("spark.executor.cores", "1") \
    .config("spark.driver.memory", "1G") \
    .config("spark.jars.packages", ",".join(packages)) \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

# Read from Kafka
df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "machine_data") \
    .option("startingOffsets", "latest") \
    .load()

    
# Parse value as JSON
json_df = df.selectExpr("CAST(value AS STRING) as json_str") \
    .select(from_json(col("json_str"), schema).alias("data")) \
    .select("data.*") \
    .withColumn("event_time", (col("timestamp") / 1000).cast("timestamp"))



# Define 1-minute window for aggregation


# Define 1-minute window for aggregation
windowed_df = json_df \
    .withWatermark("event_time", "1 minutes") \
    .groupBy(
        window(col("event_time"), "1 minute"),
        col("asset_id")
    ).agg(
        expr("sum(case when status = 1 then 5 else 0 end)").alias("run_seconds"),
        expr("sum(case when status = 2 then 5 else 0 end)").alias("idle_seconds"),
        expr("sum(case when status = 0 then 5 else 0 end)").alias("stopped_seconds"),
        expr("sum(case when status = 408 then 5 else 0 end)").alias("offline_seconds")
    ) \
    .withColumn("total_seconds", expr("run_seconds + idle_seconds + stopped_seconds + offline_seconds")) \
    .withColumn("data_loss", expr("GREATEST(60 - total_seconds, 0)")) \
    .withColumn("minute", col("window.start")) \
    .withColumn("ts", expr("CAST(current_timestamp() AS timestamp)")) \
    .select(
        "ts",
        "minute",
        "asset_id",
        "run_seconds",
        "idle_seconds",
        "stopped_seconds",
        "offline_seconds",
        "data_loss"
    )

# Output to console (or replace with write to file/db/sink)
# query = windowed_df.writeStream \
#     .outputMode("update") \
#     .format("console") \
#     .option("truncate", "false") \
#     .option("numRows", 50) \
#     .start()    


def write_to_kafka(batch_df, batch_id):
    batch_df.selectExpr("to_json(struct(*)) AS value") \
        .write \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "localhost:9092") \
        .option("topic", "machine_1_minute") \
        .save()


query = windowed_df.writeStream \
    .trigger(processingTime="1 minute") \
    .foreachBatch(write_to_kafka) \
    .outputMode("update") \
    .start()


query.awaitTermination()