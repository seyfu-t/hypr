from pypresence import Presence
import time

client_id = "1355263237129637939"

RPC = Presence(client_id)
RPC.connect()

start_time = int(time.time()) - (9999 * 3600)  # Fake "9999 hours ago"

RPC.update(
    details="Finding the imposter",
    state="in vent",
    start=start_time,
    large_text="Impඞster"
)

while True:
    time.sleep(15)  # Keep the connection alive
