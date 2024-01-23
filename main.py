import argparse
from tools.sound import extract_audio_from_video, read_audio, get_sound_bumps, write_manifest, split_by_manifest

def main(args):
    extract_audio_from_video(args.video, "output/sound.wav")
    data, rate = read_audio("output/sound.wav")
    bumps = get_sound_bumps(data, rate, 1)
    write_manifest(bumps, args.time)
    split_by_manifest(args.video, "manifest.json")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="This script allows you to extract major clips from complete video based on sound.")
    parser.add_argument('--video', type=str, default='clip.mp4', help='Specify the video path.')
    parser.add_argument('--time', type=int, default=10, help='Specify clips timing.')
    args = parser.parse_args()
    main(args)
