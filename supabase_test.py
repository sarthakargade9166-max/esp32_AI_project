from supabase import create_client

url = "https://asbyinrlipuwfkcfpvag.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFzYnlpbnJsaXB1d2ZrY2ZwdmFnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQwODE4ODUsImV4cCI6MjA5OTY1Nzg4NX0.gl1w-Ff6_zrgiUtm31g5UmrTAMk1Bz-U7cACaOAULIw"

supabase = create_client(url, key)

data = {
    "queue_count": 15,
    "predicted_wait": 30
}

response = supabase.table("queue_data").insert(data).execute()

print("Inserted Successfully")
print(response)