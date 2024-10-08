#!/usr/bin/python3
import os
import sys
import json
import logging
import warnings
import whisper_timestamped
import subprocess

# Set up basic logging
logger = logging.getLogger()
logging.basicConfig(level=logging.INFO)

# Suppress specific warnings
warnings.filterwarnings(
    "ignore",
    message="FP16 is not supported on CPU; using FP32 instead",
    category=UserWarning
)

def extract_audio(input_filename):
    """Extract audio from the video file and save it as a .wav file."""
    audio_filename = os.path.splitext(input_filename)[0] + "_audio.wav"
    command = [
        "ffmpeg", "-i", input_filename, "-ac", "1", "-ar", "16000", "-vn", "-y", audio_filename
    ]
    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return audio_filename
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error: {e.stderr.decode()}")
        return None

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
            # Extract audio from the video file
            audio_path = extract_audio(input_filename)
            if not audio_path:
                logger.error("Audio extraction failed.")
                return

            srt_filename = os.path.splitext(os.path.basename(input_filename))[0] + ".json"
            export_srtfilename = os.path.join(os.path.dirname(input_filename), srt_filename)

            # Load the Whisper model with whisper_timestamped
            model = whisper_timestamped.load_model("large", device="cpu")

            # Transcribe audio with word-level timestamps and apply VAD
            options = {
                "language": "en",
                "trust_whisper_timestamps": False,
                "use_backend_timestamps": True,
                "verbose": True,
                "refine_whisper_precision": 0.5,
                "naive_approach": True,
                "vad": "auditok"  # Enable VAD to remove non-speech segments
            }
            results = whisper_timestamped.transcribe(model, audio_path, **options)
            segments_list = results['segments']  # Extract segments with detailed word timestamps

            # Write output to JSON
            if segments_list:
                with open(export_srtfilename, "w") as f:
                    f.write("[\n")  # Start of array
                    for i, segment in enumerate(segments_list):
                        start_timecode = convert_timecode(segment['start'])
                        end_timecode = convert_timecode(segment['end'])
                        text = segment['text'].strip()

                        # Create dictionary to store subtitle data
                        data = {
                            "start": start_timecode,
                            "end": end_timecode,
                            "text": text
                        }
                        print(data)  # For debugging
                        json.dump(data, f, indent=4)
                        if i < len(segments_list) - 1:
                            f.write(",\n")  # Add a comma after each item except the last
                    f.write("\n]")  # End of array
            else:
                logger.info("No transcriptions generated.")
    except Exception as e:
        logger.error(f"Error generating subtitles: {e}")
        return

if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.info("Usage: python gen_subs.py <video_file_path>")
        sys.exit(1)

    input_filename = sys.argv[1]
    if not os.path.exists(input_filename):
        logger.info(f"File {input_filename} does not exist.")
        sys.exit(1)

    make_subtitles(input_filename)
