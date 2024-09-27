#!/usr/bin/python3
import os
import gc
import sys
import json
import logging
import warnings
from faster_whisper import WhisperModel

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Set up basic logging
logger = logging.getLogger()
logging.basicConfig(level=logging.INFO)

# Suppress specific warnings
warnings.filterwarnings(
    "ignore",
    message="FP16 is not supported on CPU; using FP32 instead",
    category=UserWarning
)

def convert_timecode(timecode):
    """Convert timecode from seconds to HH:MM:SS,FFF format."""
    total_milliseconds = int(timecode * 1000)  # Convert seconds to milliseconds
    hours = total_milliseconds // 3600000
    minutes = (total_milliseconds % 3600000) // 60000
    seconds = (total_milliseconds % 60000) // 1000
    milliseconds = total_milliseconds % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"

def make_subtitles(input_filename):
    try:
        if os.path.isfile(input_filename):
            srt_filename = os.path.splitext(os.path.basename(input_filename))[0] + ".json"
            export_srtfilename = os.path.join(os.path.dirname(input_filename), srt_filename)

            model = WhisperModel("base", device="cpu", compute_type="int8")
            # model = WhisperModel("large-v2", device="cpu", compute_type="int8")

            # Transcribe audio
            audio_file = input_filename
            segments, _ = model.transcribe(audio_file, beam_size=5)  # segments is a generator

            # Convert generator to a list
            segments_list = list(segments)

            if segments_list:
                with open(export_srtfilename, "w") as f:
                    f.write("[\n")  # Start of array
                    for i, segment in enumerate(segments_list):
                        start_timecode = convert_timecode(segment.start)
                        end_timecode = convert_timecode(segment.end)
                        data = {
                            "start": start_timecode,
                            "end": end_timecode,
                            "text": segment.text.strip()
                        }
                        json.dump(data, f, indent=4)
                        if i < len(segments_list) - 1:
                            f.write(",\n")  # Add a comma after each item except the last
                    f.write("\n]")  # End of array
            else:
                logger.info("No transcriptions generated.")
    except Exception as e:
        print(e)
        return

if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.info("Usage: python gen_subs.py <audio_file_path>")
        sys.exit(1)

    input_filename = sys.argv[1]
    if not os.path.exists(input_filename):
        logger.info(f"Audio file {input_filename} does not exist.")
        sys.exit(1)

    make_subtitles(input_filename)
