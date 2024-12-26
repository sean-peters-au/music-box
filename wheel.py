import cadquery as cq
import math

# ----------------------
# PARAMETRIC DIMENSIONS
# ----------------------

outer_diameter = 13.0
outer_radius   = outer_diameter / 2.0

total_height   = 20.0   # cylinder runs from Z=0 to Z=20

# "Stepped" wall thickness:
#   - bottom 2 mm:  1 mm wall
#   - middle 16 mm: 4 mm wall
#   - top 2 mm:     1 mm wall
bottom_section_height = 2.0
middle_section_height = 16.0
top_section_height    = 2.0

bottom_wall_thickness = 1.0
middle_wall_thickness = 4.0
top_wall_thickness    = 1.0

# Pins
num_pins        = 16
pin_radial_bump = 0.5    # how far the pin extends radially beyond the cylinder OD
pin_width       = 0.5    # tangential width
pin_height      = 1.0    # vertical dimension

# --------------------------------------
# 1) CREATE THE OUTER CYLINDER (Z=0→20)
# --------------------------------------
# By default, extrude() from a workplane at Z=0 goes up to Z=20, so the bottom is at Z=0.

outer_cylinder = (
    cq.Workplane("XY")  
    .circle(outer_radius)            # radius = 6.5 mm
    .extrude(total_height)           # from Z=0 up to Z=20
)

# ---------------------------------------------
# 2) CREATE THE STEPPED INTERIOR AS 3 EXTRUDES
# ---------------------------------------------
# We build three inner cylinders (bottom, middle, top) and union them, 
# then subtract from the outer cylinder. Each is placed at the correct Z-offset.

# 2a) Bottom 2 mm: 1 mm wall => inner radius = 6.5 - 1 = 5.5 mm
inner_bottom = (
    cq.Workplane("XY")
    .circle(outer_radius - bottom_wall_thickness)  # 5.5 mm
    .extrude(bottom_section_height)                # extrude 2 mm high, Z=0..2
)

# 2b) Middle 16 mm: 4 mm wall => inner radius = 6.5 - 4 = 2.5 mm
inner_middle = (
    cq.Workplane("XY")
    .workplane(offset=bottom_section_height)           # shift up by 2 mm
    .circle(outer_radius - middle_wall_thickness)      # 2.5 mm
    .extrude(middle_section_height)                    # extrude 16 mm, Z=2..18
)

# 2c) Top 2 mm: 1 mm wall => inner radius = 6.5 - 1 = 5.5 mm
inner_top = (
    cq.Workplane("XY")
    .workplane(offset=bottom_section_height + middle_section_height)  # shift up 18 mm
    .circle(outer_radius - top_wall_thickness)                        # 5.5 mm
    .extrude(top_section_height)                                      # 2 mm, Z=18..20
)

inner_cylinder = inner_bottom.union(inner_middle).union(inner_top)

# Subtract the interior from the outer cylinder
wheel = outer_cylinder.cut(inner_cylinder)

# ---------------------------------------------
# 3) ADD PINS IN A SPIRAL FROM Z=4..16
# ---------------------------------------------
#
# We place 16 pins around the cylinder, each at a different angle (0..360) 
# and a different height (4..16).  The cylinder bottom is at Z=0, 
# so these pins are all in the central region.

pins = cq.Workplane("XY")

z_min = 4.0
z_max = 16.0
z_span = z_max - z_min  # 12 mm

for i in range(num_pins):
    angle_deg = i * (360.0 / num_pins)
    angle_rad = math.radians(angle_deg)
    
    # Spiral in Z
    z_pin_center = z_min + (z_span * i / (num_pins - 1))  # from 4..16
    
    # Cylinder surface in X/Y
    x_center = outer_radius * math.cos(angle_rad)
    y_center = outer_radius * math.sin(angle_rad)
    
    # We'll define a pin as a small "box" extending radially outward from the cylinder’s surface.
    z_bottom = z_pin_center - (pin_height / 2.0)
    
    single_pin = (
        cq.Workplane("XY")
        .box(
            length=pin_radial_bump,  # 0.5 mm radial extension
            width=pin_width,         # 0.5 mm wide tangentially
            height=pin_height,       # 1.0 mm tall
            centered=(False, True, False)
        )
        # Rotate that box around Z by angle_deg
        .rotate((0, 0, 0), (0, 0, 1), angle_deg)
        # Translate so the "cylinder-facing" face is at (outer_radius, 0, z_bottom)
        .translate((x_center, y_center, z_bottom))
    )
    pins = pins.union(single_pin)

wheel_with_pins = wheel.union(pins)

# ---------------------------------------------
# 4) EXPORT TO STL
# ---------------------------------------------
wheel_with_pins.val().exportStl("music_box_wheel_test.stl", tolerance=0.01)
print("Exported 'music_box_wheel_test.stl'.")