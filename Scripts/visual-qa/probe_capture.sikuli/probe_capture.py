# Oculix/Jython adapter: fresh native frame recognition and exact-window capture.
# Input is opt-in, after recognition and owned-window/focus validation.
# No game launch, locale modification or save actions occur here.
from org.sikuli.script import Finder, Pattern
from java.lang import Thread
from java.io import File
from javax.imageio import ImageIO
import os
import json
import subprocess
import sys
import time

def wait(seconds):
    Thread.sleep(int(seconds * 1000))

mode, root, window_id = sys.argv[1:4]
helper = sys.argv[5] if len(sys.argv) > 5 else os.path.join(os.path.dirname(os.path.dirname(root)), "visual-qa-tools", "window-info")
# Reconcile ownership before each capture, including a reused window ID.
info = json.loads(subprocess.check_output([helper]))
windows = [w for w in info["windows"] if str(w["kCGWindowNumber"]) == window_id]
if len(windows) != 1:
    raise RuntimeError("Owned fixture window disappeared or became ambiguous")
window = windows[0]
if mode == "click":
    input_helper = os.path.join(os.path.dirname(helper), "target-input")
    if subprocess.call([input_helper, "focus", str(window["kCGWindowOwnerPID"]), window_id]):
        raise RuntimeError("Cannot focus owned fixture")
    # Settle after the last activation, before native capture and recognition.
    wait(1.2)
raw = os.path.join(root, "native.png")
rgb = os.path.join(root, "native-rgb.png")
if os.path.exists(raw):
    raise RuntimeError("Refusing existing capture output")
status = subprocess.call(["/usr/sbin/screencapture", "-x", "-o", "-l", window_id, raw])
if status or not os.path.isfile(raw):
    raise RuntimeError("Native window capture failed")
if subprocess.call(["/opt/homebrew/bin/magick", raw, "-alpha", "off", "-depth", "8", "PNG24:" + rgb]):
    raise RuntimeError("Native frame normalization failed")
image = ImageIO.read(File(rgb))
if image is None or image.getWidth() < 640 or image.getHeight() < 360:
    raise RuntimeError("Missing or unexpectedly small native frame")
if mode in ["guard", "click"]:
    marker = sys.argv[4]
    finder = Finder(image)
    try:
        finder.find(Pattern(marker).similar(0.90))
        if not finder.hasNext():
            raise RuntimeError("Expected menu marker is absent; no input performed")
        match = finder.next()
        if mode == "click":
            bounds = window["kCGWindowBounds"]
            px = bounds["X"] + (match.getX() + match.getW()/2.0) * bounds["Width"]/image.getWidth()
            py = bounds["Y"] + (match.getY() + match.getH()/2.0) * bounds["Height"]/image.getHeight()
            if subprocess.call([input_helper, "click", str(window["kCGWindowOwnerPID"]), window_id, str(px), str(py)]):
                raise RuntimeError("Guarded input refused")
            print("VN_HUMAN_GUARDED_CLICK: %s,%s" % (px, py))
    finally:
        finder.destroy()
elif mode != "smoke":
    raise RuntimeError("Unknown capture mode")
print("VN_HUMAN_CAPTURE_OK: %sx%s %s" % (image.getWidth(), image.getHeight(), raw))
