import os

with open('styles.css', 'rb') as f:
    content = f.read()

# Find the last valid } and truncate after it
last_brace = content.rfind(b'}')
if last_brace != -1:
    # Check if there are animations after it
    # We want to keep the animations we added
    animations_start = content.find(b'/* Animations */')
    if animations_start != -1:
        # Find the last } of the animations
        last_anim_brace = content.rfind(b'}')
        # Wait, the mangled line also ends with }
        # Let's search for the mangled prefix
        mangled_start = content.find(b'@\x00 k\x00 e\x00 y\x00 f\x00 r\x00 a\x00 m\x00 e\x00 s\x00')
        if mangled_start != -1:
            content = content[:mangled_start]
        elif content.find(b'@ k e y f r a m e s') != -1:
             mangled_start = content.find(b'@ k e y f r a m e s')
             content = content[:mangled_start]

with open('styles.css', 'wb') as f:
    f.write(content)
