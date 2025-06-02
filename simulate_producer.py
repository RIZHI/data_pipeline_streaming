import time
import json
import random
from kafka import KafkaProducer

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    key_serializer=lambda k: k.encode('utf-8'),
)

STATUSES = [0, 1, 2,408]

def generate_machine_data(asset_id):
    return {
        "asset_id": asset_id,
        "timestamp": int(time.time() * 1000),
        "status": random.choice(STATUSES)
    }

try:
    while True:
        for asset_id in range(1, 100):  # 500 assets
            data = generate_machine_data(str(asset_id))
            producer.send("machine_data", key=str(asset_id), value=data)
        producer.flush()
        print(f"Sent data for 500 assets at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        time.sleep(5)
except KeyboardInterrupt:
    print("Stopped producing.")
finally:
    producer.close()
