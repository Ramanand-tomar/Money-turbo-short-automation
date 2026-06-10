from moviepy import Clip, ColorClip, CompositeVideoClip, vfx


# FadeIn
def fadein_transition(clip: Clip, t: float) -> Clip:
    return clip.with_effects([vfx.FadeIn(t)])


# FadeOut
def fadeout_transition(clip: Clip, t: float) -> Clip:
    return clip.with_effects([vfx.FadeOut(t)])


# SlideIn
def slidein_transition(clip: Clip, t: float, side: str) -> Clip:
    width, height = clip.size

    # MoviePy 内置 SlideIn 在当前这条处理链里对全屏素材不稳定，
    # 会出现“逻辑上应用了转场，但画面几乎看不出变化”的情况。
    # 这里改成显式黑底 + 位移动画，保证转场效果可见且行为可控。
    def position(current_time: float):
        progress = min(max(current_time / max(t, 0.001), 0), 1)

        if side == "left":
            return (-width + width * progress, 0)
        if side == "right":
            return (width - width * progress, 0)
        if side == "top":
            return (0, -height + height * progress)
        if side == "bottom":
            return (0, height - height * progress)
        return (0, 0)

    background = ColorClip(size=(width, height), color=(0, 0, 0)).with_duration(
        clip.duration
    )
    moving_clip = clip.with_position(position)
    return CompositeVideoClip([background, moving_clip], size=(width, height)).with_duration(
        clip.duration
    )


# SlideOut
def slideout_transition(clip: Clip, t: float, side: str) -> Clip:
    width, height = clip.size
    transition_start = max(clip.duration - t, 0)

    # SlideOut 同样改成显式位移，保证片段末尾能稳定滑出画面。
    def position(current_time: float):
        if current_time <= transition_start:
            return (0, 0)

        progress = min(
            max((current_time - transition_start) / max(t, 0.001), 0), 1
        )

        if side == "left":
            return (-width * progress, 0)
        if side == "right":
            return (width * progress, 0)
        if side == "top":
            return (0, -height * progress)
        if side == "bottom":
            return (0, height * progress)
        return (0, 0)

    background = ColorClip(size=(width, height), color=(0, 0, 0)).with_duration(
        clip.duration
    )
    moving_clip = clip.with_position(position)
    return CompositeVideoClip([background, moving_clip], size=(width, height)).with_duration(
        clip.duration
    )


# Ken Burns Zoom
def ken_burns_zoom(clip: Clip, zoom_ratio: float = 1.05, direction: str = "in") -> Clip:
    duration = clip.duration
    if not duration or duration <= 0:
        return clip

    w, h = clip.size

    def effect(get_frame, t):
        frame = get_frame(t)  # shape (h, w, c)
        
        # Calculate current zoom factor
        if direction == "in":
            factor = 1.0 + (zoom_ratio - 1.0) * (t / duration)
        else:
            factor = zoom_ratio - (zoom_ratio - 1.0) * (t / duration)

        if factor == 1.0:
            return frame

        # Crop a centered region based on the factor
        crop_w = int(w / factor)
        crop_h = int(h / factor)
        
        # Ensure crop size is even and bounded
        crop_w = max(2, min(w, crop_w - (crop_w % 2)))
        crop_h = max(2, min(h, crop_h - (crop_h % 2)))
        
        x1 = (w - crop_w) // 2
        y1 = (h - crop_h) // 2
        x2 = x1 + crop_w
        y2 = y1 + crop_h
        
        # Slice frame and cast to uint8 to be safe for PIL
        import numpy as np
        cropped = frame[y1:y2, x1:x2].astype(np.uint8)
        
        # Resize back to original w, h using PIL
        from PIL import Image
        img = Image.fromarray(cropped)
        resampling = getattr(Image, "Resampling", None)
        if resampling:
            resample_filter = resampling.LANCZOS
        else:
            resample_filter = Image.LANCZOS
            
        resized_img = img.resize((w, h), resample_filter)
        return np.array(resized_img)

    return clip.transform(effect)


# Color Grade Preset
def color_grade(clip: Clip, preset: str) -> Clip:
    if not preset or preset == "none":
        return clip

    def apply_preset(frame):
        import numpy as np
        img = frame.astype(np.float32)
        if preset == "warm":
            img[..., 0] = img[..., 0] * 1.15  # Red
            img[..., 1] = img[..., 1] * 1.05  # Green
            img[..., 2] = img[..., 2] * 0.9   # Blue
        elif preset == "cool":
            img[..., 0] = img[..., 0] * 0.9   # Red
            img[..., 1] = img[..., 1] * 0.95  # Green
            img[..., 2] = img[..., 2] * 1.2   # Blue
        elif preset == "dramatic":
            # Desaturate 30%
            r = img[..., 0]
            g = img[..., 1]
            b = img[..., 2]
            luma = 0.299 * r + 0.587 * g + 0.114 * b
            luma = np.expand_dims(luma, axis=-1)
            img = img * 0.7 + luma * 0.3
            # Contrast boost
            img = (img - 128.0) * 1.3 + 128.0
        return np.clip(img, 0, 255).astype(np.uint8)

    return clip.image_transform(apply_preset)


# Speed Ramp
def speed_ramp(clip: Clip, slow_start: float = 0.5, fast_middle: float = 1.5, slow_end: float = 0.5) -> Clip:
    from moviepy import concatenate_videoclips
    duration = clip.duration
    if not duration or duration <= 0.6:
        return clip
    t1 = duration / 3.0
    t2 = 2.0 * duration / 3.0
    c1 = clip.subclipped(0, t1).with_speed_scaled(slow_start)
    c2 = clip.subclipped(t1, t2).with_speed_scaled(fast_middle)
    c3 = clip.subclipped(t2, duration).with_speed_scaled(slow_end)
    return concatenate_videoclips([c1, c2, c3])


# Glitch helpers
def glitch_single_clip(clip: Clip, duration: float = 0.3, position: str = "both") -> Clip:
    from moviepy import concatenate_videoclips
    clip_dur = clip.duration
    if not clip_dur:
        return clip

    def apply_glitch_frame(frame):
        import numpy as np
        import random
        h, w, c = frame.shape
        glitched = frame.copy()
        num_bands = random.randint(3, 8)
        for _ in range(num_bands):
            y1 = random.randint(0, max(0, h - 10))
            y2 = random.randint(y1 + 5, min(y1 + 50, h))
            shift = random.randint(-40, 40)
            if shift == 0:
                continue
            band = glitched[y1:y2, :, :]
            glitched[y1:y2, :, :] = np.roll(band, shift, axis=1)
        return glitched

    def glitch_frame(frame):
        import random
        if random.random() < 0.7:
            return apply_glitch_frame(frame)
        return frame

    if clip_dur <= duration:
        return clip.image_transform(glitch_frame)

    t_half = duration / 2.0
    clips = []
    
    # Start part
    if position in ("start", "both"):
        start_part = clip.subclipped(0, t_half).image_transform(glitch_frame)
        clips.append(start_part)
        mid_start = t_half
    else:
        mid_start = 0

    # End part
    if position in ("end", "both"):
        end_part = clip.subclipped(clip_dur - t_half, clip_dur).image_transform(glitch_frame)
        mid_end = clip_dur - t_half
    else:
        end_part = None
        mid_end = clip_dur

    # Middle clean part
    middle_part = clip.subclipped(mid_start, mid_end)
    clips.append(middle_part)

    # Append end part
    if end_part is not None:
        clips.append(end_part)

    return concatenate_videoclips(clips)


def glitch_transition(clip1: Clip, clip2: Clip, duration: float = 0.3) -> Clip:
    from moviepy import concatenate_videoclips
    t_half = duration / 2.0
    c1_end = clip1.subclipped(clip1.duration - t_half, clip1.duration)
    c2_start = clip2.subclipped(0, t_half)
    g1 = glitch_single_clip(c1_end, duration, "both")
    g2 = glitch_single_clip(c2_start, duration, "both")
    return concatenate_videoclips([g1, g2])

