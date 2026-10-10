# Oculix/Jython: recognize fresh scenes; restore exact fixture focus, never click.
from org.sikuli.script import Finder, Pattern
from javax.imageio import ImageIO
from java.io import File
from java.awt.image import BufferedImage
import json
import os
import subprocess
import sys
import time


def rgb_buffer(image):
    # macOS PNGs have an alpha channel; trained crops are RGB. OpenCV requires
    # equal channel types. Convert the fresh buffer before taking any region.
    rgb = BufferedImage(image.getWidth(), image.getHeight(), BufferedImage.TYPE_3BYTE_BGR)
    graphics = rgb.createGraphics()
    try:
        graphics.drawImage(image, 0, 0, None)
    finally:
        graphics.dispose()
    return rgb


def recognizes(image, scene, root):
    rgb = rgb_buffer(image)
    for marker in scene['markers']:
        x, y, w, h = marker.get('searchRegion', marker['region'])
        # A subimage shares its parent's raster stride/offset. Finder needs a
        # standalone compact buffer, otherwise a positive crop can fail.
        region = rgb_buffer(rgb.getSubimage(x, y, w, h))
        threshold = marker.get('brightTextThreshold')
        if threshold is not None:
            region = bright_text(region, threshold)
        finder = Finder(region)
        try:
            template = rgb_buffer(ImageIO.read(File(os.path.join(root, marker['file']))))
            if threshold is not None:
                template = bright_text(template, threshold)
            finder.find(Pattern(template).similar(marker['similarity']))
            found = finder.hasNext()
        finally:
            finder.destroy()
        if found != marker.get('present', True):
            return False
    return True


def bright_text(image, threshold):
    # Preserve the complete white subtitle glyphs, exclude moving video floor.
    for y in range(image.getHeight()):
        for x in range(image.getWidth()):
            pixel = image.getRGB(x, y)
            white = min((pixel >> 16) & 255, (pixel >> 8) & 255, pixel & 255) >= threshold
            image.setRGB(x, y, -1 if white else -16777216)
    return image


mode, recipe_path, output = sys.argv[1:4]
root = os.path.dirname(recipe_path)
recipe = json.load(open(recipe_path))
if mode == 'verify':
    results = []
    for name, scene in recipe['scenes'].items():
        expected = ImageIO.read(File(os.path.join(root, scene['positive'])))
        if not recognizes(expected, scene, root):
            raise RuntimeError('Positive scene control failed: ' + name)
        for control in scene.get('additionalPositive', []):
            if not recognizes(ImageIO.read(File(control['file'])), scene, root):
                raise RuntimeError('Additional positive scene failed: ' + name)
        for negative in scene['negative']:
            wrong = ImageIO.read(File(os.path.join(root, negative)))
            if recognizes(wrong, scene, root):
                raise RuntimeError('Wrong scene accepted: ' + name + ' / ' + negative)
        for control in scene.get('additionalNegative', []):
            if recognizes(ImageIO.read(File(control['file'])), scene, root):
                raise RuntimeError('Neighboring text accepted: ' + name)
        results.append({'scene': name, 'positiveControls': 1 + len(scene.get('additionalPositive', [])),
                        'negativeControls': len(scene['negative']) + len(scene.get('additionalNegative', []))})
    json.dump({'result': 'pass', 'scenes': results}, open(output, 'w'), indent=2)
    print('VN_SIX_SCENES_VERIFIED')
elif mode == 'wait':
    scene_name, helper, seconds, input_helper = sys.argv[4:8]
    scene = recipe['scenes'][scene_name]
    deadline = time.time() + float(seconds)
    attempts = 0
    latest = os.path.join(output, 'latest.png')
    focus_events = []
    identity = None
    while time.time() < deadline:
        info = json.loads(subprocess.check_output([helper]))
        windows = [w for w in info['windows'] if w.get('kCGWindowName') == 'NoImNotAHuman']
        if len(windows) != 1 or not info['screenRecordingAllowed']:
            raise RuntimeError('Owned readable fixture window disappeared')
        win = windows[0]
        if win['kCGWindowBounds'] != recipe['logicalBounds']:
            raise RuntimeError('Window geometry changed')
        current = [win['kCGWindowOwnerPID'], win['kCGWindowNumber']]
        if identity is None:
            identity = current
        if current != identity:
            raise RuntimeError('Fixture window identity changed')
        # Java startup and movie transitions can take focus after the launcher
        # activated Wine. Recover here, after startup and throughout waiting.
        if not focus_events or info['frontmostApplication']['pid'] != identity[0]:
            event = {'previousFrontmost': info['frontmostApplication'], 'windowIdentity': identity,
                     'elapsedSeconds': float(seconds) - (deadline - time.time())}
            subprocess.check_call([input_helper, 'focus', str(identity[0]), str(identity[1])])
            time.sleep(1.2)
            after = json.loads(subprocess.check_output([helper]))
            event['restored'] = after['frontmostApplication']['pid'] == identity[0]
            focus_events.append(event)
            json.dump(focus_events, open(os.path.join(output, 'focus-events.json'), 'w'), indent=2)
            if not event['restored']:
                raise RuntimeError('Exact fixture focus could not be restored')
            continue
        if subprocess.call(['/usr/sbin/screencapture', '-x', '-o', '-l', str(win['kCGWindowNumber']), latest]):
            raise RuntimeError('Native capture failed')
        # ImageIO reads bytes afresh; never let a filename cache reuse an old frame.
        image = ImageIO.read(File(latest))
        if image is None or [image.getWidth(), image.getHeight()] != recipe['nativeDimensions']:
            raise RuntimeError('Native capture dimensions changed')
        attempts += 1
        matched = recognizes(image, scene, root)
        after = json.loads(subprocess.check_output([helper]))
        if after['frontmostApplication']['pid'] != identity[0]:
            continue  # Include lazy Java/Finder initialization in the focus gate.
        if matched:
            os.rename(latest, os.path.join(output, 'native.png'))
            json.dump({'scene': scene_name, 'result': 'pass', 'attempts': attempts, 'window': win,
                       'focusEvents': focus_events, 'frontmostPid': identity[0]},
                      open(os.path.join(output, 'recognition.json'), 'w'), indent=2)
            print('VN_SIX_SCENE_OK:' + scene_name)
            break
        time.sleep(.3)
    else:
        json.dump({'scene': scene_name, 'result': 'timeout', 'attempts': attempts},
                  open(os.path.join(output, 'recognition.json'), 'w'), indent=2)
        raise RuntimeError('Expected scene timeout: ' + scene_name)
else:
    raise RuntimeError('Unknown mode')
