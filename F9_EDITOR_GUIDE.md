# F9 Editor - Quick Reference Guide

## 🎮 Hotkeys

| Key | Action |
|-----|--------|
| **F5** | Stop replay completely |
| **F7** | Pause/Resume replay |
| **F9** | Open interactive editor |
| **ESC** | Stop replay (legacy) |

---

## 🔘 Editor Buttons

### Navigation & Preview
- **👁️ Preview Position** - Move mouse to action's position (no replay)
- **▶️ Play from here** - Jump to action and resume replay

### Editing
- **Insert Before** - Add new event before selected
- **Insert After** - Add new event after selected
- **Modify** - Edit selected event's properties
- **Delete** - Remove selected event

### Control
- **💾 Save & Resume (F7)** - Save changes and continue
- **❌ Discard Changes** - Close without saving
- **⏹️ Stop Replay (F5)** - Stop completely

---

## 📋 Common Workflows

### 1. Check Where a Click Happens
```
1. Press F9 during replay
2. Uncheck "Mouse Moves" filter
3. Find the click event (m_down)
4. Click "👁️ Preview Position"
5. Mouse jumps to that position!
```

### 2. Fix Wrong Click Coordinates
```
1. Press F9 during replay
2. Select the wrong click
3. Click "👁️ Preview Position" to verify
4. Edit coordinates in detail panel
5. Click "Modify"
6. Click "👁️ Preview Position" again to confirm
7. Save & Resume
```

### 3. Skip to Specific Action
```
1. Press F9 during replay
2. Find the action you want
3. Click "▶️ Play from here"
4. Replay continues from that point
```

### 4. Test Multiple Click Positions
```
1. Press F9 during replay
2. Uncheck "Mouse Moves"
3. Select first click
4. Click "👁️ Preview Position"
5. Select next click
6. Click "👁️ Preview Position"
7. Repeat to verify all positions
```

---

## 💡 Tips

**Performance:**
- Always uncheck "Mouse Moves" unless you need them
- This reduces 10,000 events to ~100 actionable items

**Preview Position:**
- Works only with mouse events (clicks, moves, scrolls)
- Automatically applies resolution transformation
- Window title shows confirmation for 2 seconds
- No replay execution - just mouse movement

**Play from Here:**
- Jumps to selected event instantly
- Timing is reset for smooth continuation
- Works with both `replay()` and `replay_with_markers()`

**Editing:**
- Always preview position after modifying coordinates
- Use Insert Before/After for adding delays
- Delete unwanted actions safely

---

## 🎯 Example: Verify All Clicks in a Replay

```python
# Start replay
python test_f9_editor.py

# During replay:
1. Press F9
2. Uncheck "Mouse Moves"
3. You see only clicks and keys
4. Select first m_down event
5. Click "👁️ Preview Position"
6. Check if mouse is in right place
7. Select next m_down event
8. Click "👁️ Preview Position"
9. Repeat for all clicks
10. Click "Discard Changes" when done
```

---

## 🐛 Troubleshooting

**Preview doesn't work:**
- Make sure you selected a mouse event (not keyboard)
- Check that the event has x, y coordinates
- Verify pynput is installed: `pip install pynput`

**Mouse goes to wrong position:**
- Check if resolution transformation is active
- Verify coordinates in detail panel
- Try modifying and previewing again

**Can't see the action:**
- Use filters to hide mouse moves
- Look for m_down, m_up, k_down, k_up events
- Check the timestamp to find the right moment
