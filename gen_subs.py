import os
import sys
import json
import logging
import tempfile
import ffmpeg
import gc
import wave
import webrtcvad
from faster_whisper import WhisperModel
from datetime import datetime

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Set up basic logging
logger = logging.getLogger()
logging.basicConfig(level=logging.INFO)

def format_timestamp(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02}:{minutes:02}:{secs:06.3f}"

def extract_audio(video_path):
    """Extract audio from video and convert to mono WAV format."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
        temp_wav_path = temp_wav.name
    try:
        ffmpeg.input(video_path).output(temp_wav_path, ac=1, ar='16000').run(overwrite_output=True, quiet=False)
        return temp_wav_path
    except ffmpeg.Error as e:
        logger.error(f"FFmpeg error: {e.stderr.decode()}")
        return None

def read_wave(path):
    """Reads a .wav file and verifies format compatibility with webrtcvad."""
    with wave.open(path, "rb") as wf:
        num_channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        sample_rate = wf.getframerate()
        pcm_data = wf.readframes(wf.getnframes())

        if num_channels != 1 or sample_width != 2 or sample_rate != 16000:
            raise ValueError("Audio file must be 16 kHz, mono, 16-bit PCM.")

        return pcm_data, sample_rate

def detect_non_speech(audio_path, aggressiveness=2, frame_duration_ms=30):
    """Detect non-speech segments in the audio file using WebRTC VAD."""
    vad = webrtcvad.Vad(aggressiveness)
    pcm_data, sample_rate = read_wave(audio_path)

    frame_size = int(sample_rate * frame_duration_ms / 1000) * 2  # Bytes per frame (16-bit audio)
    frames = [pcm_data[i:i + frame_size] for i in range(0, len(pcm_data), frame_size)]

    non_speech_segments = []
    prev_speech_end = 0
    timestamp = 0.0

    for i, frame in enumerate(frames):
        # Only process frames that are the correct length for the chosen frame duration
        if len(frame) != frame_size:
            continue

        is_speech = vad.is_speech(frame, sample_rate)
        current_time = timestamp + frame_duration_ms / 1000.0

        if not is_speech:
            if prev_speech_end != timestamp:
                non_speech_segments.append({
                    "start": format_timestamp(prev_speech_end),
                    "end": format_timestamp(current_time)
                })

        if is_speech:
            prev_speech_end = current_time  # Update end of speech segment

        timestamp = current_time  # Update the frame timestamp

    return non_speech_segments, audio_path

def make_subtitles(audio_path):
    """Generate subtitles for a given audio file, optionally adjusting for non-speech segments."""
    try:
        if os.path.isfile(audio_path):

            audio_path = extract_audio(input_filename)

            non_speech_segments, processed_audio_path = detect_non_speech(audio_path)

            srt_filename = os.path.splitext(os.path.basename(audio_path))[0] + ".json"
            export_srtfilename = os.path.join(os.path.dirname(audio_path), srt_filename)

            model = WhisperModel("base", device="cpu", compute_type="int8")
            logger.info("Transcribing audio with Whisper...")
            segments, _ = model.transcribe(audio_path, beam_size=5)

            segments_list = list(segments)

            subtitles = [
                {
                    "start": format_timestamp(segment.start),
                    "end": format_timestamp(segment.end),
                    "text": segment.text.strip()
                }
                for segment in segments_list
            ]

            if non_speech_segments:
                logger.info("Adjusting subtitles based on non-speech segments.")
                subtitles = adjust_subtitles(non_speech_segments, subtitles)

            with open(export_srtfilename, "w") as f:
                json.dump(subtitles, f, indent=4)

            gc.collect()

            if os.path.exists(processed_audio_path):
                os.remove(processed_audio_path)

    except Exception as e:
        logger.error(f"Error generating subtitles: {e}")

def adjust_start_time(original_start, non_speech_segments):
    """Adjust the subtitle start time to avoid non-speech segments."""
    # Parse the original start time string to a datetime object
    original_start_dt = datetime.strptime(original_start, "%H:%M:%S.%f")

    for segment in non_speech_segments:
        start_time = datetime.strptime(segment['start'], "%H:%M:%S.%f")
        end_time = datetime.strptime(segment['end'], "%H:%M:%S.%f")

        if start_time <= original_start_dt < end_time:
            # If within non-speech segment, return end_time as new start time
            return end_time
    # If not within any non-speech segment, return the original start time
    return original_start_dt


def adjust_subtitles(non_speech_segments, subtitles):
    """Adjust subtitles to avoid starting during non-speech segments."""
    adjusted_subtitles = []

    for subtitle in subtitles:
        original_start = subtitle["start"]
        adjusted_start_dt = adjust_start_time(original_start, non_speech_segments)

        # Convert adjusted start time back to string format if it was adjusted
        adjusted_subtitle = subtitle.copy()
        adjusted_subtitle["start"] = format_timestamp(adjusted_start_dt.timestamp())

        adjusted_subtitles.append(adjusted_subtitle)

    return adjusted_subtitles

if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.info("Usage: python gen_subs.py <input_filename>")
        sys.exit(1)

    input_filename = sys.argv[1]
    if not os.path.exists(input_filename):
        logger.info(f"File {input_filename} does not exist.")
        sys.exit(1)

    #
    # if audio_path:
    #     non_speech_segments, processed_audio_path = detect_non_speech(audio_path)
    make_subtitles(input_filename)

        # if os.path.exists(processed_audio_path):
        #     os.remove(processed_audio_path)
