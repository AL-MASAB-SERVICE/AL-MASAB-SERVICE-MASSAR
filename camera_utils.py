import os
from datetime import datetime

def save_event_images(image):
    if image is None:
        return None

    folder = "event_images"
    os.makedirs(folder, exist_ok=True)

    filename = f"{folder}/event_{datetime.now().timestamp()}.jpg"

    with open(filename, "wb") as f:
        f.write(image.getbuffer())

    return filename