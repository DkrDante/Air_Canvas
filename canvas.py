"""
╔══════════════════════════════════════════════════════╗
║           AIR CANVAS PRO  v4                         ║
║           Right sidebar · Gesture-first UX           ║
╚══════════════════════════════════════════════════════╝

GESTURE SYSTEM
──────────────
✦ DRAW          — point index finger, PINCH to ink
✦ ERASE         — raise index + middle fingers, PINCH to erase
✦ PAN           — open full palm, PINCH to scroll
✦ UNDO          — open palm + swipe LEFT
✦ REDO          — open palm + swipe RIGHT
✦ CLEAR         — make a fist, hold 2 seconds
✦ BRUSH SIZE    — two hands: spread/squeeze index fingers
✦ SAVE          — sidebar button or keyboard S

SIDEBAR (right edge) — hover + pinch to click
  Color swatches · Tool buttons · Brush slider · Opacity slider · Fill · Actions

KEYBOARD  [ / ]  brush    z / y  undo/redo    c  clear    q  quit
"""

import cv2, math, time
import numpy as np
from collections import deque
import mediapipe as mp

# ═══════════════════════════════════════════════════════
#  MEDIAPIPE
# ═══════════════════════════════════════════════════════
mp_hands = mp.solutions.hands
detector = mp_hands.Hands(max_num_hands=2,
                          min_detection_confidence=0.75,
                          min_tracking_confidence=0.75)

# ═══════════════════════════════════════════════════════
#  PALETTE & TOOLS
# ═══════════════════════════════════════════════════════
PALETTE = [
    (255,255,255),(255,200,80),(220,80,20),(180,200,20),
    (40,200,40),(20,240,160),(30,30,220),(30,140,240),
    (180,80,220),(200,50,120),
]
TOOLS   = ["Draw","Erase","Line","Rect","Circle","Triangle","Arrow","Pan"]
T_ICON  = {"Draw":"PEN","Erase":"ERS","Line":"LNE","Rect":"RCT",
           "Circle":"CRC","Triangle":"TRI","Arrow":"ARW","Pan":"PAN"}

# ═══════════════════════════════════════════════════════
#  SIDEBAR GEOMETRY  (right side)
# ═══════════════════════════════════════════════════════
SB_W        = 165
PAD         = 10
SWATCH_SZ   = 28
SWATCH_PAD  = 5
BTN_H       = 46
BAR_H       = 20
GAP         = 12

# ═══════════════════════════════════════════════════════
#  APP STATE
# ═══════════════════════════════════════════════════════
cur_color   = PALETTE[0]
cur_tool    = "Draw"
brush_sz    = 6
eraser_sz   = 32
opacity     = 1.0
filled      = False

prev_wx = prev_wy = 0
start_sx = start_sy = 0
was_pinched = False
undo_stack, redo_stack = [], []

pan_x = pan_y = 0
pan_start_sx = pan_start_sy = pan_ox = pan_oy = 0
CANVAS_W = CANVAS_H = 0

# Gesture state
pinch_buf   = deque(maxlen=6)
cur_bx      = deque(maxlen=5)
cur_by      = deque(maxlen=5)
vel_buf     = deque(maxlen=8)           # recent dx for swipe detection
prev_sx_g   = prev_sy_g = 0            # previous screen x/y for velocity

fist_start  = 0.0                       # time fist was first detected
fist_active = False
last_undo_t = last_redo_t = 0.0        # debounce swipe actions
gesture_hint      = ""                  # displayed on screen
gesture_hint_time = 0.0

# ═══════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════
def save_undo(c):
    undo_stack.append(c.copy())
    redo_stack.clear()
    if len(undo_stack) > 20: undo_stack.pop(0)

def s2w(sx, sy): return int(sx - pan_x), int(sy - pan_y)

def show_hint(txt):
    global gesture_hint, gesture_hint_time
    gesture_hint = txt
    gesture_hint_time = time.time()

def rr(img, x1, y1, x2, y2, col, r=7, t=-1):
    x1,y1,x2,y2 = int(x1),int(y1),int(x2),int(y2)
    r = max(1, min(r, (x2-x1)//2, (y2-y1)//2))
    if t == -1:
        cv2.rectangle(img,(x1+r,y1),(x2-r,y2),col,-1)
        cv2.rectangle(img,(x1,y1+r),(x2,y2-r),col,-1)
        for cx,cy in [(x1+r,y1+r),(x2-r,y1+r),(x1+r,y2-r),(x2-r,y2-r)]:
            cv2.circle(img,(cx,cy),r,col,-1)
    else:
        cv2.rectangle(img,(x1+r,y1),(x2-r,y2),col,t)
        cv2.rectangle(img,(x1,y1+r),(x2,y2-r),col,t)
        for cx,cy in [(x1+r,y1+r),(x2-r,y1+r),(x1+r,y2-r),(x2-r,y2-r)]:
            cv2.circle(img,(cx,cy),r,col,t)

def op_line(canvas, p1, p2, col, th, op):
    if op >= 0.99:
        cv2.line(canvas, p1, p2, col, th, cv2.LINE_AA); return
    ov = canvas.copy()
    cv2.line(ov, p1, p2, col, th, cv2.LINE_AA)
    cv2.addWeighted(ov, op, canvas, 1-op, 0, canvas)

def op_shape(canvas, fn, op):
    if op >= 0.99: fn(canvas); return
    ov = canvas.copy(); fn(ov)
    cv2.addWeighted(ov, op, canvas, 1-op, 0, canvas)

def draw_shape(surf, tool, sx,sy,ex,ey, col, th, fill):
    if   tool == "Line":
        cv2.line(surf,(sx,sy),(ex,ey),col,th,cv2.LINE_AA)
    elif tool == "Rect":
        if fill: cv2.rectangle(surf,(sx,sy),(ex,ey),col,-1)
        cv2.rectangle(surf,(sx,sy),(ex,ey),col,th,cv2.LINE_AA)
    elif tool == "Circle":
        r = int(math.hypot(ex-sx,ey-sy))
        if fill: cv2.circle(surf,(sx,sy),r,col,-1)
        cv2.circle(surf,(sx,sy),r,col,th,cv2.LINE_AA)
    elif tool == "Triangle":
        mid = (sx+ex)//2
        pts = np.array([[mid,sy],[sx,ey],[ex,ey]],np.int32)
        if fill: cv2.fillPoly(surf,[pts],col)
        cv2.polylines(surf,[pts],True,col,th,cv2.LINE_AA)
    elif tool == "Arrow":
        cv2.arrowedLine(surf,(sx,sy),(ex,ey),col,th,tipLength=0.25,line_type=cv2.LINE_AA)

# ═══════════════════════════════════════════════════════
#  FINGER STATE DETECTION
# ═══════════════════════════════════════════════════════
def fingers_up(lm, w, h):
    """Return list of booleans [thumb, index, middle, ring, pinky] = extended."""
    def pt(i): return np.array([lm[i].x*w, lm[i].y*h])
    tips   = [4, 8, 12, 16, 20]
    bases  = [2, 5, 10, 14, 18]
    up = []
    # Thumb: compare x distance (left/right depending on handedness — use tip vs base)
    thumb_up = pt(4)[0] > pt(3)[0] if pt(0)[0] < pt(9)[0] else pt(4)[0] < pt(3)[0]
    up.append(thumb_up)
    for tip, base in zip(tips[1:], bases[1:]):
        up.append(pt(tip)[1] < pt(base)[1] - 10)
    return up  # [thumb, index, middle, ring, pinky]

def count_up(fu): return sum(fu)

def is_fist(fu):     return count_up(fu) == 0
def is_point(fu):    return fu[1] and not fu[2] and not fu[3] and not fu[4]
def is_two_up(fu):   return fu[1] and fu[2] and not fu[3] and not fu[4]
def is_open(fu):     return count_up(fu) >= 4

# ═══════════════════════════════════════════════════════
#  SIDEBAR LAYOUT  (x coords offset by canvas_w - SB_W)
# ═══════════════════════════════════════════════════════
def build_layout(h, sb_x):
    """sb_x = left edge of sidebar on screen."""
    items = []
    y = 58

    items.append(("lbl",-1,y,y+14,"COLOR",None)); y += 18
    for i,(bgr) in enumerate(PALETTE):
        row = i//5; col = i%5
        lx  = sb_x + PAD + col*(SWATCH_SZ+SWATCH_PAD)
        ly  = y + row*(SWATCH_SZ+SWATCH_PAD)
        items.append(("pal",i,ly,ly+SWATCH_SZ,None,{"x1":lx,"x2":lx+SWATCH_SZ}))
    rows = math.ceil(len(PALETTE)/5)
    y += rows*(SWATCH_SZ+SWATCH_PAD) + GAP

    items.append(("lbl",-1,y,y+14,"TOOLS",None)); y += 18
    for i,t in enumerate(TOOLS):
        items.append(("tool",i,y,y+BTN_H,t,None)); y += BTN_H+4
    y += GAP

    items.append(("lbl",-1,y,y+14,"BRUSH",None)); y += 18
    items.append(("brush",0,y,y+BAR_H,None,None)); y += BAR_H+GAP
    items.append(("lbl",-1,y,y+14,"OPACITY",None)); y += 18
    items.append(("opacity",0,y,y+BAR_H,None,None)); y += BAR_H+GAP

    items.append(("fill",0,y,y+BTN_H-4,None,None)); y += BTN_H
    for i,lab in enumerate(["UNDO","REDO","CLEAR","SAVE"]):
        items.append(("act",i,y,y+BTN_H-4,lab,None)); y += BTN_H
    return items

def hit(mx, my, layout, sb_x):
    if mx < sb_x: return None, None
    for sec,idx,y1,y2,extra,xdata in layout:
        if sec == "lbl": continue
        if not (y1 <= my <= y2): continue
        if sec == "pal":
            if xdata["x1"] <= mx <= xdata["x2"]: return sec, idx
        else:
            return sec, idx
    return None, None

def draw_sidebar(frame, h, w, layout, sb_x, hov_s, hov_i, spread):
    global brush_sz, opacity, filled, cur_color, cur_tool

    # Glass background
    ov = frame.copy()
    cv2.rectangle(ov,(sb_x,0),(w,h),(16,16,22),-1)
    cv2.addWeighted(ov,0.93,frame,0.07,0,frame)
    cv2.line(frame,(sb_x,0),(sb_x,h),(55,55,72),1)

    # Header strip
    cv2.rectangle(frame,(sb_x,0),(w,52),(22,32,50),-1)
    cv2.putText(frame,"AIR",   (sb_x+PAD,24),cv2.FONT_HERSHEY_DUPLEX,0.82,(120,210,255),1)
    cv2.putText(frame,"CANVAS",(sb_x+PAD,44),cv2.FONT_HERSHEY_DUPLEX,0.46,(70,140,200),1)
    cv2.line(frame,(sb_x+PAD,52),(w-PAD,52),(50,55,70),1)

    for sec,idx,y1,y2,extra,xdata in layout:
        is_hov = (hov_s == sec and hov_i == idx)

        if sec == "lbl":
            cv2.putText(frame,extra,(sb_x+PAD,y2-1),
                        cv2.FONT_HERSHEY_SIMPLEX,0.34,(88,92,118),1)
            continue

        if sec == "pal":
            bgr = PALETTE[idx]
            x1s, x2s = xdata["x1"], xdata["x2"]
            rr(frame,x1s,y1,x2s,y2,bgr,r=5)
            if bgr == cur_color and cur_tool != "Erase":
                rr(frame,x1s-3,y1-3,x2s+3,y2+3,(255,255,255),r=6,t=2)
            elif is_hov:
                rr(frame,x1s-2,y1-2,x2s+2,y2+2,(180,190,255),r=6,t=1)
            continue

        if sec == "tool":
            active = (cur_tool == extra)
            bg = (44,110,200) if active else ((42,52,72) if is_hov else (24,24,32))
            rr(frame,sb_x+PAD,y1,w-PAD,y2,bg,r=6)
            if active: rr(frame,sb_x+PAD,y1,w-PAD,y2,(90,150,255),r=6,t=2)
            ic = (180,195,225) if active else (95,100,130)
            cv2.putText(frame,T_ICON.get(extra,"---"),
                        (sb_x+PAD+8,y1+BTN_H//2+7),cv2.FONT_HERSHEY_SIMPLEX,0.38,ic,1)
            tc = (255,255,255) if active else (155,160,195)
            cv2.putText(frame,extra.upper(),
                        (sb_x+PAD+38,y1+BTN_H//2+7),cv2.FONT_HERSHEY_SIMPLEX,0.42,tc,1)
            continue

        def slider(top, val, maxv, acc, label):
            bx1 = sb_x+PAD; bx2 = w-PAD; by = top+BAR_H//2
            cv2.rectangle(frame,(bx1,by-4),(bx2,by+4),(34,34,48),-1)
            fx = int(bx1+(bx2-bx1)*(val/maxv))
            cv2.rectangle(frame,(bx1,by-4),(fx,by+4),acc,-1)
            cv2.circle(frame,(fx,by),8,(255,255,255),-1)
            cv2.circle(frame,(fx,by),8,(150,155,180),1)
            cv2.putText(frame,label,(bx2-44,top+14),cv2.FONT_HERSHEY_SIMPLEX,0.34,(155,160,190),1)

        if sec == "brush":
            slider(y1,brush_sz,40,(75,155,240),f"{brush_sz}px"); continue
        if sec == "opacity":
            slider(y1,opacity,1.0,(200,140,80),f"{int(opacity*100)}%"); continue

        if sec == "fill":
            bg = (28,88,50) if filled else (26,26,36)
            if is_hov: bg = tuple(min(c+20,255) for c in bg)
            rr(frame,sb_x+PAD,y1,w-PAD,y2,bg,r=6)
            fc = (80,220,110) if filled else (110,115,145)
            cv2.putText(frame,f"FILL  {'ON' if filled else 'OFF'}",
                        (sb_x+PAD+10,y1+(y2-y1)//2+7),cv2.FONT_HERSHEY_SIMPLEX,0.42,fc,1)
            continue

        if sec == "act":
            cb = {"UNDO":(48,78,120),"REDO":(48,78,120),"CLEAR":(118,42,42),"SAVE":(38,100,58)}
            bg = cb.get(extra,(50,50,70))
            if is_hov: bg = tuple(min(c+28,255) for c in bg)
            rr(frame,sb_x+PAD,y1,w-PAD,y2,bg,r=6)
            cv2.putText(frame,extra,(sb_x+PAD+12,y1+(y2-y1)//2+7),
                        cv2.FONT_HERSHEY_SIMPLEX,0.44,(215,220,240),1)
            continue

    # Two-hand indicator
    if spread is not None:
        cv2.putText(frame,f"2H {spread}px",(sb_x+PAD,h-42),
                    cv2.FONT_HERSHEY_SIMPLEX,0.34,(100,200,120),1)

    # Status strip
    cv2.rectangle(frame,(sb_x,h-20),(w,h),(20,20,28),-1)
    cv2.circle(frame,(sb_x+14,h-10),6,cur_color,-1)
    cv2.circle(frame,(sb_x+14,h-10),6,(65,65,80),1)
    cv2.putText(frame,cur_tool[:6].upper(),(sb_x+26,h-4),
                cv2.FONT_HERSHEY_SIMPLEX,0.36,(165,170,200),1)

def handle_sb_click(sec, idx, canvas):
    global cur_color, cur_tool, filled, brush_sz, opacity
    if sec == "pal":
        cur_color = PALETTE[idx]
        if cur_tool == "Erase": cur_tool = "Draw"
    elif sec == "tool":
        cur_tool = TOOLS[idx]
    elif sec == "fill":
        filled = not filled
    elif sec == "act":
        lab = ["UNDO","REDO","CLEAR","SAVE"][idx]
        if lab == "UNDO" and undo_stack:
            redo_stack.append(canvas.copy()); return undo_stack.pop()
        elif lab == "REDO" and redo_stack:
            undo_stack.append(canvas.copy()); return redo_stack.pop()
        elif lab == "CLEAR":
            save_undo(canvas); return np.zeros_like(canvas)
        elif lab == "SAVE":
            fn = f"air_canvas_{int(time.time())}.png"
            cv2.imwrite(fn, canvas); show_hint(f"💾 Saved {fn}")
    return canvas

# ═══════════════════════════════════════════════════════
#  CURSOR
# ═══════════════════════════════════════════════════════
def draw_cursor(frame, sx, sy, col, sz, pinched, tool):
    r = max(5, sz//2)
    if tool == "Pan":
        cv2.circle(frame,(sx,sy),12,(200,200,100),2)
        cv2.line(frame,(sx-16,sy),(sx+16,sy),(200,200,100),1)
        cv2.line(frame,(sx,sy-16),(sx,sy+16),(200,200,100),1)
        return
    if tool == "Erase":
        col = (200,200,200)
        cv2.rectangle(frame,(sx-r,sy-r),(sx+r,sy+r),col,2)
        return
    if pinched:
        cv2.circle(frame,(sx,sy),r,col,-1)
        cv2.circle(frame,(sx,sy),r+2,(255,255,255),1)
    else:
        cv2.circle(frame,(sx,sy),r,col,1)
        cv2.line(frame,(sx-r-6,sy),(sx+r+6,sy),(255,255,255),1)
        cv2.line(frame,(sx,sy-r-6),(sx,sy+r+6),(255,255,255),1)

# ═══════════════════════════════════════════════════════
#  GESTURE OVERLAY  (hint banner + fist progress ring)
# ═══════════════════════════════════════════════════════
def draw_gesture_ui(frame, h, w, fist_progress, hand_sx, hand_sy):
    # Hint banner (top center)
    if gesture_hint and (time.time() - gesture_hint_time) < 1.8:
        alpha = 1.0 - max(0, (time.time()-gesture_hint_time-1.2)/0.6)
        txt   = gesture_hint
        tw, _ = cv2.getTextSize(txt,cv2.FONT_HERSHEY_SIMPLEX,0.6,1)[0], None
        tw    = cv2.getTextSize(txt,cv2.FONT_HERSHEY_SIMPLEX,0.6,1)[0][0]
        bx    = w//2 - tw//2 - 16
        ov    = frame.copy()
        rr(ov, bx, 12, bx+tw+32, 46, (30,30,40), r=8)
        cv2.addWeighted(ov, 0.85*alpha, frame, 1-0.85*alpha, 0, frame)
        cv2.putText(frame,txt,(bx+16,36),cv2.FONT_HERSHEY_SIMPLEX,0.6,
                    (200,220,255),1,cv2.LINE_AA)

    # Fist hold — circular progress ring around hand
    if fist_progress > 0.05 and hand_sx > 0:
        angle = int(360 * fist_progress)
        cv2.ellipse(frame,(hand_sx,hand_sy),(28,28),
                    -90,0,angle,(60,40,160),3,cv2.LINE_AA)
        cv2.ellipse(frame,(hand_sx,hand_sy),(28,28),
                    0,0,360,(50,50,70),1,cv2.LINE_AA)
        cv2.putText(frame,"HOLD",(hand_sx-16,hand_sy+5),
                    cv2.FONT_HERSHEY_SIMPLEX,0.38,(180,140,255),1)

# ═══════════════════════════════════════════════════════
#  MAIN LOOP
# ═══════════════════════════════════════════════════════
cap    = cv2.VideoCapture(0)
canvas = None
color_idx = 0
print("Air Canvas Pro v4 — press 'q' to quit", flush=True)
print("Gestures: 1-finger=draw  2-fingers=erase  open palm=pan", flush=True)
print("          swipe left/right=undo/redo  fist 2s=clear  thumbs-up=save", flush=True)

while cap.isOpened():
    ok, frame = cap.read()
    if not ok: break
    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape
    sb_x    = w - SB_W          # sidebar left edge

    if canvas is None:
        CANVAS_W = w*3; CANVAS_H = h*3
        canvas   = np.zeros((CANVAS_H,CANVAS_W,3),np.uint8)
        pan_x = -w; pan_y = -h

    layout = build_layout(h, sb_x)

    # ── Keyboard ──────────────────────────────────────
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'): break
    elif key == ord('['): brush_sz = max(1, brush_sz-1)
    elif key == ord(']'): brush_sz = min(40, brush_sz+1)
    elif key == ord('z') and undo_stack:
        redo_stack.append(canvas.copy()); canvas = undo_stack.pop()
        show_hint("↩  Undo")
    elif key == ord('y') and redo_stack:
        undo_stack.append(canvas.copy()); canvas = redo_stack.pop()
        show_hint("↪  Redo")
    elif key == ord('f'): filled = not filled
    elif key == ord('c'):
        save_undo(canvas); canvas = np.zeros_like(canvas); show_hint("🗑  Cleared")
    elif key == ord('p'): cur_tool = "Pan" if cur_tool != "Pan" else "Draw"

    # ── Hand detection ─────────────────────────────────
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    res = detector.process(rgb)
    hov_s = hov_i = None
    spread_display  = None
    fist_progress   = 0.0
    hand_sx = hand_sy = 0

    if res.multi_hand_landmarks:
        hl = res.multi_hand_landmarks

        # ── Two-hand spread = brush size ───────────────
        if len(hl) == 2:
            l0,l1 = hl[0].landmark, hl[1].landmark
            x0,y0 = l0[8].x*w, l0[8].y*h
            x1,y1 = l1[8].x*w, l1[8].y*h
            sp = int(math.hypot(x1-x0, y1-y0))
            spread_display = sp
            brush_sz = int(np.interp(sp,[30,300],[1,40]))

        # ── Primary hand ───────────────────────────────
        lm = hl[0].landmark
        fu = fingers_up(lm, w, h)

        # Raw index tip (for cursor)
        xi = int(lm[8].x*w); yi = int(lm[8].y*h)
        cur_bx.append(xi); cur_by.append(yi)
        sx = int(np.mean(cur_bx)); sy = int(np.mean(cur_by))
        hand_sx, hand_sy = sx, sy

        # Pinch smoothing
        xt = int(lm[4].x*w); yt = int(lm[4].y*h)
        pinch_buf.append(math.hypot(xt-xi, yt-yi))
        is_pinched   = np.mean(pinch_buf) < 38
        just_clicked = is_pinched and not was_pinched
        just_released= not is_pinched and was_pinched

        # Velocity for swipe detection
        if prev_sx_g > 0:
            vel_buf.append(sx - prev_sx_g)
        prev_sx_g = sx

        # ════════════════════════════════════════════
        #  GESTURE RECOGNITION
        #
        #  Rules:
        #   - Pinch = ONLY drawing trigger. Gestures NEVER fire while pinching.
        #   - Tool switches need NOT-pinching so drawing pose cant conflict.
        #   - Fist hold 2s = clear (very deliberate, not a normal hand shape)
        #   - Swipe undo/redo only works in open-palm (all 5 fingers up)
        #   - Removed thumbs-up save — too easy to trigger accidentally
        #     Save is sidebar button or keyboard S only
        # ════════════════════════════════════════════

        # FIST HOLD 2s → clear (only when not pinching / not drawing)
        if is_fist(fu) and not is_pinched:
            if not fist_active:
                fist_active = True
                fist_start  = time.time()
            elapsed = time.time() - fist_start
            fist_progress = min(1.0, elapsed / 2.0)
            if elapsed >= 2.0:
                save_undo(canvas)
                canvas = np.zeros_like(canvas)
                show_hint("Canvas Cleared")
                fist_active = False
                fist_start  = 0.0
        else:
            fist_active   = False
            fist_progress = 0.0

        # OPEN PALM + fast swipe → undo / redo
        # Requires ALL 5 fingers up — physically impossible while pinching to draw.
        # After firing, lock BOTH directions for 1.5s so the natural return
        # motion (hand drifting back to neutral) cannot trigger the opposite action.
        SWIPE_COOLDOWN = 1
        if is_open(fu) and not is_pinched and len(vel_buf) >= 6:
            avg_vel = np.mean(list(vel_buf))
            now = time.time()
            both_clear = (now - last_undo_t) > SWIPE_COOLDOWN and (now - last_redo_t) > SWIPE_COOLDOWN
            if both_clear:
                if avg_vel < -22 and undo_stack:
                    redo_stack.append(canvas.copy())
                    canvas = undo_stack.pop()
                    show_hint("Undo")
                    last_undo_t = last_redo_t = now
                    vel_buf.clear()
                elif avg_vel > 22 and redo_stack:
                    undo_stack.append(canvas.copy())
                    canvas = redo_stack.pop()
                    show_hint("Redo")
                    last_undo_t = last_redo_t = now
                    vel_buf.clear()

        # TOOL AUTO-SWITCH by finger count
        # Only fires: in canvas zone + NOT pinching + NOT a fist
        # Single index finger (draw pose) never accidentally switches mode
        if sx < sb_x and not is_pinched and not is_fist(fu):
            if is_open(fu) and cur_tool != "Pan":
                # All 5 fingers = Pan. Very deliberate open hand.
                cur_tool = "Pan"
                show_hint("Pan")
            elif is_two_up(fu) and cur_tool not in ["Erase"]:
                # Index + middle only = Erase
                cur_tool = "Erase"
                show_hint("Erase")
            elif is_point(fu) and cur_tool in ["Pan", "Erase"]:
                # Back to single index = Draw
                cur_tool = "Draw"
                show_hint("Draw")


        # ════════════════════════════════════════════
        #  SIDEBAR ZONE
        # ════════════════════════════════════════════
        if sx >= sb_x:
            hov_s, hov_i = hit(sx, sy, layout, sb_x)
            if is_pinched:
                if hov_s == "brush":
                    ratio = (sx - sb_x - PAD) / max(1, SB_W - 2*PAD)
                    brush_sz = max(1, min(40, int(ratio*40)))
                elif hov_s == "opacity":
                    ratio = (sx - sb_x - PAD) / max(1, SB_W - 2*PAD)
                    opacity = round(max(0.05, min(1.0, ratio)), 2)
            if just_clicked and hov_s not in (None,"lbl","brush","opacity"):
                canvas = handle_sb_click(hov_s, hov_i, canvas)
            prev_wx = prev_wy = 0

        # ════════════════════════════════════════════
        #  CANVAS ZONE
        # ════════════════════════════════════════════
        else:
            col_use = (0,0,0) if cur_tool == "Erase" else cur_color
            sz_use  = eraser_sz if cur_tool == "Erase" else brush_sz
            draw_cursor(frame, sx, sy, col_use, sz_use, is_pinched, cur_tool)
            wx, wy = s2w(sx, sy)

            # PAN
            if cur_tool == "Pan":
                if just_clicked:
                    pan_start_sx, pan_start_sy = sx, sy
                    pan_ox, pan_oy = pan_x, pan_y
                if is_pinched:
                    pan_x = int(np.clip(pan_ox+(sx-pan_start_sx), -(CANVAS_W-w//2), w//2))
                    pan_y = int(np.clip(pan_oy+(sy-pan_start_sy), -(CANVAS_H-h//2), h//2))
                prev_wx = prev_wy = 0

            # DRAW / SHAPE
            else:
                if not is_pinched:
                    if prev_wx != 0 or prev_wy != 0:
                        if cur_tool not in ["Draw","Erase"]:
                            sw_x, sw_y = s2w(start_sx, start_sy)
                            op_shape(canvas,
                                lambda c: draw_shape(c,cur_tool,sw_x,sw_y,wx,wy,
                                                     col_use,sz_use,filled),
                                opacity)
                    prev_wx = prev_wy = 0
                else:
                    if just_clicked:
                        start_sx, start_sy = sx, sy
                        prev_wx, prev_wy   = wx, wy
                        save_undo(canvas)
                    if cur_tool in ["Draw","Erase"]:
                        if prev_wx != 0 or prev_wy != 0:
                            op_line(canvas,(prev_wx,prev_wy),(wx,wy),
                                    col_use, sz_use,
                                    1.0 if cur_tool=="Erase" else opacity)
                        prev_wx, prev_wy = wx, wy
                    else:
                        draw_shape(frame,cur_tool,start_sx,start_sy,sx,sy,
                                   col_use,sz_use,filled)
                        prev_wx, prev_wy = wx, wy

        was_pinched = is_pinched

    else:
        was_pinched = False
        prev_wx = prev_wy = 0
        fist_active = False
        pinch_buf.clear(); cur_bx.clear(); cur_by.clear(); vel_buf.clear()

    # ── Composite infinite canvas onto frame ──────────
    cx1 = max(0,-pan_x); cy1 = max(0,-pan_y)
    cx2 = min(CANVAS_W,cx1+w); cy2 = min(CANVAS_H,cy1+h)
    fx1 = max(0,pan_x);  fy1 = max(0,pan_y)
    fw  = cx2-cx1; fh = cy2-cy1
    if fw > 0 and fh > 0:
        cv_sl = canvas[cy1:cy1+fh, cx1:cx1+fw]
        fr_sl = frame [fy1:fy1+fh, fx1:fx1+fw]
        frame[fy1:fy1+fh, fx1:fx1+fw] = cv2.addWeighted(fr_sl,1.0,cv_sl,1.0,0)

    # ── Canvas edge lines ─────────────────────────────
    for ewx in [0, CANVAS_W]:
        ex_s = ewx + pan_x
        if 0 < ex_s < sb_x: cv2.line(frame,(ex_s,0),(ex_s,h),(55,55,85),1)
    for ewy in [0, CANVAS_H]:
        ey_s = ewy + pan_y
        if 0 < ey_s < h:    cv2.line(frame,(0,ey_s),(sb_x,ey_s),(55,55,85),1)

    # ── Sidebar ───────────────────────────────────────
    draw_sidebar(frame, h, w, layout, sb_x, hov_s, hov_i, spread_display)

    # ── Gesture UI overlay ────────────────────────────
    draw_gesture_ui(frame, h, w, fist_progress, hand_sx, hand_sy)

    # ── HUD bottom-left ───────────────────────────────
    hud = f" {cur_tool}  sz:{brush_sz}  op:{int(opacity*100)}%  fill:{'on' if filled else 'off'}"
    cv2.putText(frame,hud,(8,h-6),cv2.FONT_HERSHEY_SIMPLEX,0.36,(140,145,170),1)

    cv2.imshow("Air Canvas Pro v4", frame)

cap.release()
cv2.destroyAllWindows()
