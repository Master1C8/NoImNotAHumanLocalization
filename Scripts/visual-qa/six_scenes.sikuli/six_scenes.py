# Oculix/Jython: recognize fresh scenes and guard exact fixture focus/input.
from org.sikuli.script import Finder, Pattern
from javax.imageio import ImageIO
from java.io import File
from java.awt.image import BufferedImage
import json
import os
import subprocess
import sys
import time

template_cache = {}


def prepared_template(root, marker):
    # Run markers are immutable and hash-bound before worker startup.
    key = (os.path.join(root, marker['file']), marker.get('brightTextThreshold'))
    if key not in template_cache:
        template = rgb_buffer(ImageIO.read(File(key[0])))
        if key[1] is not None:
            template = bright_text(template, key[1])
        width, height = template.getWidth(), template.getHeight()
        pixels = template.getRGB(0, 0, width, height, None, 0, width)
        foreground = [i for i, pixel in enumerate(pixels) if (pixel & 255) == 255]
        template_cache[key] = (template, foreground)
    return template_cache[key]


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
            template, foreground = prepared_template(root, marker)
            finder.find(Pattern(template).similar(marker['similarity']))
            found = finder.hasNext()
            coverage = marker.get('whiteForegroundCoverage')
            if found and coverage is not None:
                if threshold is None:
                    raise RuntimeError('Foreground coverage needs a white-glyph marker')
                match = finder.next()
                width, height = template.getWidth(), template.getHeight()
                actual_pixels = region.getRGB(int(match.x), int(match.y), width, height, None, 0, width)
                found = bool(foreground) and sum((actual_pixels[i] & 255) == 255 for i in foreground) >= len(foreground) * coverage
        finally:
            finder.destroy()
        if found != marker.get('present', True):
            return False
    return True


def bright_text(image, threshold):
    # Preserve the complete white subtitle glyphs, exclude moving video floor.
    width, height = image.getWidth(), image.getHeight()
    pixels = image.getRGB(0, 0, width, height, None, 0, width)
    for i in range(len(pixels)):
        pixel = pixels[i]
        white = min((pixel >> 16) & 255, (pixel >> 8) & 255, pixel & 255) >= threshold
        pixels[i] = -1 if white else -16777216
    image.setRGB(0, 0, width, height, pixels, 0, width)
    return image


def main(argv):
    mode, recipe_path, output = argv[:3]
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
    elif mode == 'serve':
        # Initialize Finder before any time-sensitive movie; Java can take focus once.
        sample = recipe['scenes']['settings']
        recognizes(ImageIO.read(File(sample['positive'])), sample, root)
        for marker in recipe.get('learnedCaption', {}).get('markers', []):
            prepared_template(root, marker)
        print('VN_WORKER_READY')
        sys.stdout.flush()
        for line in sys.stdin:
            command = json.loads(line)
            if command.get('mode') == 'quit':
                break
            try:
                main(['wait', recipe_path, command['output'], command['scene'],
                      command['helper'], str(command['timeout']), command['input']])
                print('VN_WORKER_RESULT:' + json.dumps({'result': 'pass'}))
            except Exception as error:
                print('VN_WORKER_RESULT:' + json.dumps({'result': 'fail', 'error': str(error)}))
            sys.stdout.flush()
    elif mode == 'wait':
        scene_name, helper, seconds, input_helper = argv[3:7]
        observing_intro = scene_name == 'intro-to-door'
        scrolling_collection = scene_name == 'collection-scroll'
        scene = recipe['scenes']['door-far' if observing_intro else 'collection' if scrolling_collection else scene_name]
        deadline = time.time() + float(seconds)
        attempts = 0
        latest = os.path.join(output, 'latest.png')
        focus_events = []
        identity = None
        bright_previous = None
        stable_since = None
        camera_previous = None
        camera_stable_since = None
        pointer_centered = False
        camera_events = []
        scroll_events = []
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
            if info['frontmostApplication']['pid'] != identity[0]:
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
            if scrolling_collection and not matched and recognizes(image, recipe['scenes']['collection-top'], root):
                if len(scroll_events) >= 4:
                    raise RuntimeError('Collection scroll limit reached before target rows')
                before = os.path.join(output, 'before-scroll-%02d.png' % (len(scroll_events) + 1))
                import shutil
                shutil.copyfile(latest, before)
                subprocess.check_call([input_helper, 'scroll', str(identity[0]), str(identity[1]), '-1800'])
                scroll_events.append({'action': 'scroll', 'value': -1800, 'attempt': attempts,
                                      'windowIdentity': identity, 'guard': 'collection-top', 'native': before})
                json.dump(scroll_events, open(os.path.join(output, 'scroll-events.json'), 'w'), indent=2)
                time.sleep(.8)
                continue
            if observing_intro and matched and not pointer_centered:
                # The first doorway frame is still followed by mouse-driven camera
                # motion. Center only after fresh visual recognition, then require
                # the doorway again and a settled camera before returning a frame.
                subprocess.check_call([input_helper, 'move', str(identity[0]), str(identity[1]), '710', '460'])
                pointer_centered = True
                camera_events.append({'action': 'move', 'values': [710, 460], 'attempt': attempts,
                                      'windowIdentity': identity, 'guard': 'door-far'})
                json.dump(camera_events, open(os.path.join(output, 'camera-events.json'), 'w'), indent=2)
                continue
            camera_region = scene.get('stableImageRegion')
            if camera_region:
                if not matched:
                    camera_previous = None
                    camera_stable_since = None
                else:
                    x, y, w, h = camera_region
                    samples = []
                    for row in range(y, y + h, 8):
                        for col in range(x, x + w, 8):
                            pixel = image.getRGB(col, row)
                            samples.extend([(pixel >> 16) & 255, (pixel >> 8) & 255, pixel & 255])
                    rmse = ((sum((a-b)**2 for a,b in zip(samples,camera_previous)) / float(len(samples)))**.5 / 255
                            if camera_previous is not None else 1)
                    if rmse > .02 or camera_stable_since is None:
                        camera_stable_since = time.time()
                    camera_previous = samples
                    matched = time.time() - camera_stable_since >= .6
            bright_region = scene.get('stableBrightRegion')
            if matched and bright_region:
                x, y, w, h = bright_region
                signature = []
                for row in range(y, y + h, 2):
                    for col in range(x, x + w, 2):
                        pixel = image.getRGB(col, row)
                        signature.append(min((pixel >> 16) & 255, (pixel >> 8) & 255, pixel & 255) >= 220)
                count = sum(signature)
                changed = (sum(a != b for a, b in zip(signature, bright_previous))
                           if bright_previous is not None else len(signature))
                if count < 70 or changed > max(5, count * .015):
                    stable_since = time.time()
                bright_previous = signature
                matched = count >= 70 and stable_since is not None and time.time() - stable_since >= .6
            if observing_intro and not matched:
                learned = recipe.get('learnedCaption')
                caption = os.path.join(output, 'caption.png')
                if learned and not os.path.exists(caption) and recognizes(image, learned, root):
                    import shutil
                    shutil.copyfile(latest, caption)
                evidence = os.path.join(output, 'movie-frames')
                if not os.path.isdir(evidence):
                    os.mkdir(evidence)
                import shutil
                shutil.copyfile(latest, os.path.join(evidence, '%04d.png' % attempts))
            if matched:
                os.rename(latest, os.path.join(output, 'native.png'))
                json.dump({'scene': scene_name, 'result': 'pass', 'attempts': attempts, 'window': win,
                           'focusEvents': focus_events, 'cameraEvents': camera_events,
                           'scrollEvents': scroll_events, 'frontmostPid': identity[0]},
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


if __name__ == "__main__":
    main(sys.argv[1:])
