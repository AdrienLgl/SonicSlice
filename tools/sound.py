import soundfile as sf
import pyloudnorm as pyln
import numpy as np
import matplotlib.pyplot as plt
import subprocess
import json
import csv
import json
import os
import shlex
import subprocess


def split_by_manifest(filename, manifest, vcodec="copy", acodec="copy",
                      extra="", **kwargs):
    """ Split video into segments based on the given manifest file.

    Arguments:
        filename (str)      - Location of the video.
        manifest (str)      - Location of the manifest file.
        vcodec (str)        - Controls the video codec for the ffmpeg video
                            output.
        acodec (str)        - Controls the audio codec for the ffmpeg video
                            output.
        extra (str)         - Extra options for ffmpeg.
    """
    if not os.path.exists(manifest):
        print("File does not exist: %s" % manifest)
        raise SystemExit

    with open(manifest) as manifest_file:
        manifest_type = manifest.split(".")[-1]
        if manifest_type == "json":
            config = json.load(manifest_file)
        elif manifest_type == "csv":
            config = csv.DictReader(manifest_file)
        else:
            print("Format not supported. File must be a csv or json file")
            raise SystemExit

        # replace with docker exec
        split_cmd = ["ffmpeg", "-i", filename, "-vcodec", vcodec,
                     "-acodec", acodec, "-y"] + shlex.split(extra)
        try:
            fileext = filename.split(".")[-1]
        except IndexError as e:
            raise IndexError("No . in filename. Error: " + str(e))
        for video_config in config:
            split_args = []
            try:
                split_start = video_config["start_time"]
                split_length = video_config.get("end_time", None)
                if not split_length:
                    split_length = video_config["length"]
                filebase = video_config["rename_to"]
                if fileext in filebase:
                    filebase = ".".join(filebase.split(".")[:-1])

                split_args += ["-ss", str(split_start), "-t",
                               str(split_length), filebase + "." + fileext]
                print("########################################################")
                print("About to run: " + " ".join(split_cmd + split_args))
                print("########################################################")
                subprocess.check_output(split_cmd + split_args)
            except KeyError as e:
                print("############# Incorrect format ##############")
                if manifest_type == "json":
                    print("The format of each json array should be:")
                    print("{start_time: <int>, length: <int>, rename_to: <string>}")
                elif manifest_type == "csv":
                    print("start_time,length,rename_to should be the first line ")
                    print("in the csv file.")
                print("#############################################")
                print(e)
                raise SystemExit

def read_audio(audio_path):
    data, rate = sf.read(audio_path) # load audio (with shape (samples, channels))
    meter = pyln.Meter(rate) # create BS.1770 meter
    loudness = meter.integrated_loudness(data) # measure loudness
    return data, rate


def extract_audio_from_video(input_path, output_path, sample_rate=44100):
    """
    Extracts audio from a video in WAV format.

    :param input_path: Path to the input video.
    :param output_path: Path to save the WAV audio file.
    :param sample_rate: Audio sample rate (default: 44100).
    """
    command = [
        'ffmpeg',
        '-i', input_path,
        '-vn',  # Disable video
        '-acodec', 'pcm_s16le',  # PCM 16-bit little-endian audio codec
        '-ar', str(sample_rate),  # Sample rate
        '-ac', '2',  # Number of channels (stereo)
        output_path
    ]
    try:
        subprocess.run(command, check=True)
        print(f"Audio extraction successful. File saved at: {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error during audio extraction: {e}")


def get_sound_bumps(audio_data, sample_rate, threshold):
    # amplitude calculation with euclidean norm
    amp = np.sqrt(np.sum(audio_data**2, axis=1))
    reference = 1.0
    # decibels calculation
    decibels = 20 * np.log10(amp / reference)
    # calculate video time
    time = np.arange(0, len(audio_data)) / sample_rate
    # find indices
    indices = np.where(decibels > threshold)[0]

    # find bumps
    bumps = []
    bump_threshold = 5
    for i in range(1, len(indices)):
        if indices[i] - indices[i - 1] > bump_threshold:
            bumps.append(time[indices[i]])
    return bumps


def write_manifest(bumps, clip_timing=10):
    clip_timer = 0
    start = 0
    timings = []
    for bump in bumps:
        if clip_timer == 0:
            start = bump
        clip_timer += bump
        if (bump-start) >= clip_timing:
            dump = {}
            dump["start_time"] = round(start) - 10
            dump["length"] = round(bump-start) + 10
            dump["rename_to"] = f"clip-{len(timings)}"
            timings.append(dump)
            clip_timer = 0
    with open("manifest.json", 'w') as json_file:
        json.dump(timings, json_file, indent=2)
            
    
