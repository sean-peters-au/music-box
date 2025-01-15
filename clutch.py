import cadquery as cq
import math

# Build a full circle from two arcs:
#  - Arc 1: from (-10,0) to (10,0), radius= +10 (CCW)
#  - Arc 2: from (10,0) back to (-10,0), radius= -10 (CW)

demo = (
    cq.Workplane("XY")
    # Move to left side
    .moveTo(-10, 0)
    # Arc to right side (CCW)
    .radiusArc((10, 0), 10)
    # Arc back to left side (CW)
    .radiusArc((-10, 0), -10)
    .close()
    # Extrude a small distance so we can visualize in 3D
    .extrude(1.0)
)

demo.val().exportStl("arc_inversion_demo.stl", tolerance=0.01)
print("Exported 'arc_inversion_demo.stl'.")