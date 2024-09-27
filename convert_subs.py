import json
import os
import re
import sys
import webvtt
import argparse
from datetime import timedelta
# from pycaption import CaptionConverter, EBUSTLReader, EBUSTLWriter, CaptionSet
from pysrt import SubRipFile, SubRipItem, SubRipTime
from pysubs2 import SSAFile, SSAEvent

if getattr(sys, 'frozen', False):
    runpath = os.path.dirname(sys.executable)
else:
    runpath = os.path.abspath(os.path.dirname(__file__))

# Function to convert timecodes from string to timedelta
def parse_timecode(timecode):
    timecode = timecode.replace(",", ".")  # Support both comma and dot formats for milliseconds
    parts = timecode.split(':')
    seconds = float(parts[-1])
    minutes = int(parts[-2])
    hours = int(parts[-3])
    return timedelta(hours=hours, minutes=minutes, seconds=seconds)

# Function to convert timecodes to string (from timedelta) ensuring the right format
def format_timecode(subrip_time):
    hours = subrip_time.hours
    minutes = subrip_time.minutes
    seconds = subrip_time.seconds
    milliseconds = subrip_time.milliseconds
    return f"{hours:02}:{minutes:02}:{seconds:02}.{milliseconds:03}"  # Use . for milliseconds

# Load subtitle based on extension
def load_subtitle(file_path):
    extension = os.path.splitext(file_path)[1].lower()

    if extension == '.srt':
        return load_srt(file_path)
    elif extension == '.vtt':
        return load_vtt(file_path)
    elif extension == '.ass' or extension == '.ssa':
        return load_ass(file_path)
    elif extension == '.sbv':
        return load_sbv(file_path)
    elif extension == '.lrc':
        return load_lrc(file_path)
    elif extension == '.stl':
        return load_stl(file_path)  # STL support added
    else:
        raise ValueError(f"Unsupported file extension: {extension}")

# Function to load STL files using pycaption and convert them to JSON structure
def load_stl(file_path):
    with open(file_path, 'rb') as stl_file:
        stl_content = stl_file.read()
    converter = CaptionConverter()
    caption_set = converter.read(stl_content, EBUSTLReader())

    # Convert the STL captions to a JSON structure
    subtitles = []
    for lang in caption_set.get_languages():
        for caption in caption_set.get_captions(lang):
            subtitles.append({
                "start": format_caption_time(caption.start),
                "end": format_caption_time(caption.end),
                "text": caption.nodes[0].get_text() if caption.nodes else ""
            })
    return subtitles

# Helper function to format caption time from timedelta object to "HH:MM:SS.MMM"
def format_caption_time(timedelta_obj):
    total_seconds = timedelta_obj.total_seconds()
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}.{milliseconds:03}"  # Use . for milliseconds

# Function to load SRT files
def load_srt(file_path):
    srt_data = SubRipFile.open(file_path)
    subtitles = []
    for item in srt_data:
        subtitles.append({
            "start": format_timecode(item.start),
            "end": format_timecode(item.end),
            "text": item.text.replace('\n', ' ')
        })
    return subtitles

# Function to load VTT files
def load_vtt(file_path):
    vtt = webvtt.read(file_path)
    subtitles = []
    for caption in vtt:
        subtitles.append({
            "start": format_caption_time(parse_timecode(caption.start.replace(",", "."))),  # Ensure proper format
            "end": format_caption_time(parse_timecode(caption.end.replace(",", "."))),  # Ensure proper format
            "text": caption.text.replace('\n', ' ')
        })
    return subtitles

# Function to load ASS/SSA files
def load_ass(file_path):
    ass = SSAFile.load(file_path)
    subtitles = []
    for line in ass.events:
        subtitles.append({
            "start": format_caption_time(timedelta(seconds=line.start)),
            "end": format_caption_time(timedelta(seconds=line.end)),
            "text": line.text.strip().replace('\n', ' ')
        })
    return subtitles

# Function to load SBV files
def load_sbv(file_path):
    with open(file_path, 'r') as file:
        content = file.readlines()

    subtitles = []
    start_time = None
    text_lines = []

    for line in content:
        line = line.strip()
        # Match timecode lines in SBV format (e.g., 0:00:12.345,0:00:14.678)
        if re.match(r"\d+:\d+:\d+\.\d+,\d+:\d+:\d+\.\d+", line):
            # If we already have a start_time and text, save the previous subtitle
            if start_time and text_lines:
                subtitles.append({
                    "start": start_time,
                    "end": end_time,
                    "text": ' '.join(text_lines).strip()
                })
            times = line.split(',')
            start_time = format_caption_time(parse_timecode(times[0].strip()))
            end_time = format_caption_time(parse_timecode(times[1].strip()))
            text_lines = []  # Clear text for the next subtitle
        else:
            text_lines.append(line)

    # Add the final subtitle
    if start_time and text_lines:
        subtitles.append({
            "start": start_time,
            "end": end_time,
            "text": ' '.join(text_lines).strip()
        })

    return subtitles

# Function to load LRC files
def load_lrc(file_path):
    with open(file_path, 'r') as file:
        content = file.readlines()

    subtitles = []
    for line in content:
        match = re.match(r"\[(\d+):(\d+\.\d+)\](.+)", line)
        if match:
            minutes = int(match.group(1))
            seconds = float(match.group(2))
            start_time = timedelta(minutes=minutes, seconds=seconds)
            text = match.group(3).strip()
            end_time = start_time + timedelta(seconds=2)  # Assuming a fixed 2-second duration for simplicity
            subtitles.append({
                "start": format_caption_time(start_time),
                "end": format_caption_time(end_time),
                "text": text
            })
    return subtitles

# Export subtitle into any supported format
def export_subtitle(subtitles, file_path):
    extension = os.path.splitext(file_path)[1].lower()

    if extension == '.srt':
        export_srt(subtitles, file_path)
    elif extension == '.vtt':
        export_vtt(subtitles, file_path)
    elif extension == '.ass':
        export_ass(subtitles, file_path)
    elif extension == '.sbv':
        export_sbv(subtitles, file_path)
    elif extension == '.lrc':
        export_lrc(subtitles, file_path)
    elif extension == '.stl':
        export_stl(subtitles, file_path)  # STL support added
    else:
        raise ValueError(f"Unsupported file extension: {extension}")

# Export STL (using pycaption from JSON structure back to STL)
def export_stl(subtitles, file_path):
    converter = CaptionConverter()

    # Create a CaptionSet from the subtitles
    caption_set = CaptionSet()
    captions = []
    for subtitle in subtitles:
        start = parse_timecode(subtitle['start'])
        end = parse_timecode(subtitle['end'])
        captions.append({
            "start": start,
            "end": end,
            "text": subtitle["text"]
        })

    # Convert the subtitle data into a CaptionSet
    converter.captions = captions
    stl_content = converter.write(EBUSTLWriter())

    with open(file_path, 'wb') as stl_file_out:
        stl_file_out.write(stl_content)

# Function to properly format the timecode for SRT (converting milliseconds with a comma)
def format_timecode_srt(timecode_str):
    # Convert timecode to use comma for milliseconds (SRT format)
    return timecode_str.replace(".", ",")

# Function to convert a time string (HH:MM:SS,MS) to SubRipTime object
def timecode_to_subrip_time(timecode_str):
    timecode_str = format_timecode_srt(timecode_str)  # Ensure correct format with comma for milliseconds
    hours, minutes, rest = timecode_str.split(":")
    seconds, milliseconds = rest.split(",")
    return SubRipTime(int(hours), int(minutes), int(seconds), int(milliseconds))

# Export SRT
def export_srt(subtitles, file_path):
    srt_data = SubRipFile()
    for i, subtitle in enumerate(subtitles):
        # Convert the start and end timecodes to SubRipTime objects
        start = timecode_to_subrip_time(subtitle['start'])
        end = timecode_to_subrip_time(subtitle['end'])

        # Create a SubRipItem for each subtitle and add to the SubRipFile
        srt_item = SubRipItem(index=i + 1, start=start, end=end, text=subtitle['text'])
        srt_data.append(srt_item)

    srt_data.save(file_path)

# Export VTT
def export_vtt(subtitles, file_path):
    with open(file_path, 'w') as file:
        file.write("WEBVTT\n\n")
        for subtitle in subtitles:
            file.write(f"{subtitle['start']} --> {subtitle['end']}\n")
            file.write(f"{subtitle['text']}\n\n")

# Export ASS (with SSAEvent conversion)
def export_ass(subtitles, file_path):
    ass = SSAFile()
    for subtitle in subtitles:
        start = parse_timecode(subtitle['start']).total_seconds()
        end = parse_timecode(subtitle['end']).total_seconds()

        # Create SSAEvent for each subtitle
        event = SSAEvent(start=start, end=end, text=subtitle['text'])
        ass.events.append(event)

    ass.save(file_path)

# Export SBV
def export_sbv(subtitles, file_path):
    with open(file_path, 'w') as file:
        for subtitle in subtitles:
            file.write(f"{subtitle['start']},{subtitle['end']}\n")
            file.write(f"{subtitle['text']}\n\n")

# Export LRC
def export_lrc(subtitles, file_path):
    with open(file_path, 'w') as file:
        for subtitle in subtitles:
            start = parse_timecode(subtitle['start'])
            minutes, seconds = divmod(start.total_seconds(), 60)
            file.write(f"[{int(minutes)}:{seconds:.2f}]{subtitle['text']}\n")

def export_json(input_file, output_file):
    subtitles = load_subtitle(input_file)
    with open(output_file, 'w') as json_file:
        json.dump(subtitles, json_file, indent=4)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Subtitle Converter")
    parser.add_argument("input_file", help="Path to the input subtitle file")
    parser.add_argument("--output_file", help="Path to the output subtitle file")
    parser.add_argument("--to_json", action="store_true", help="Convert subtitle to JSON format")
    parser.add_argument("--from_json", action="store_true", help="Convert from JSON to subtitle format")

    args = parser.parse_args()

    if args.to_json:
        default_output_path = os.path.join(runpath, "output.json")
        export_json(args.input_file, args.output_file or default_output_path)

    elif args.from_json:
        if not args.output_file:
            print("Error: You must specify an --output_file when converting from JSON.")
        else:
            with open(args.input_file, 'r') as json_file:
                subtitles = json.load(json_file)
            export_subtitle(subtitles, args.output_file)
            print(f"Subtitles successfully converted from JSON and saved at: {args.output_file}")
    else:
        print("Please specify --to_json or --from_json")
