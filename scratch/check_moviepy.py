import moviepy
try:
    from moviepy import concatenate_videoclips
    print("Imported concatenate_videoclips directly from moviepy")
except ImportError:
    print("Could not import directly")

try:
    from moviepy.video.compositing.concatenate import concatenate_videoclips
    print("Imported from moviepy.video.compositing.concatenate")
except ImportError:
    print("Could not import from moviepy.video.compositing.concatenate")
