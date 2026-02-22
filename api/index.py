from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import statistics
import os

app = FastAPI()

# 1. Enable CORS specifically for POST requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST"], 
    allow_headers=["*"],
)

# 2. Define the exact shape of the incoming request body
class AnalyticsRequest(BaseModel):
    regions: list[str]
    threshold_ms: int

# 3. Load the JSON data safely 
# (We have to tell the code to look in the folder above the 'api' folder)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(ROOT_DIR, "q-vercel-latency.json")

with open(DATA_FILE, "r") as f:
    telemetry_data = json.load(f)

# 4. Create the POST endpoint
@app.post("/api/analytics")
def analyze_telemetry(req: AnalyticsRequest):
    results = {}
    
    # Loop through only the regions the user asked for (e.g., "amer", "emea")
    for region in req.regions:
        
        # Filter our massive dataset to just this specific region
        # Note: Make sure "region", "latency_ms", and "uptime" match the exact keys in your JSON!
        region_records = [row for row in telemetry_data if row.get("region") == region]
        
        if not region_records:
            continue
            
        # Extract lists of just the numbers we need to do math on
        latencies = [row["latency_ms"] for row in region_records]
        uptimes = [row["uptime"] for row in region_records] 
        
        # Python's built-in statistics module does the heavy math for us!
        avg_latency = statistics.mean(latencies)
        avg_uptime = statistics.mean(uptimes)
        
        # Calculate 95th Percentile: n=100 splits data into 100 buckets. Index 94 is the 95th percentile.
        p95_latency = statistics.quantiles(latencies, n=100)[94]
        
        # Count breaches (how many times latency was higher than the requested threshold)
        breaches = sum(1 for lat in latencies if lat > req.threshold_ms)
        
        # Save this region's math to our final results
        results[region] = {
            "avg_latency": avg_latency,
            "p95_latency": p95_latency,
            "avg_uptime": avg_uptime,
            "breaches": breaches
        }
        
    return results