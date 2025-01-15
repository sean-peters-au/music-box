import cadquery as cq
import math

# --------------------------------------------------------------------------------
# PART 1: CASSETTE WITH SPIRAL PINS & A NEW BASE RING
# --------------------------------------------------------------------------------

# Dimensions for the main hollow cassette cylinder
cassette_diameter       = 13.0  # mm, outer diameter of main cassette
cassette_radius         = cassette_diameter / 2.0
cassette_total_height   = 17.5
cassette_wall_thickness = 4.0   # => 5 mm ID hole (13 OD - 4 - 4 = 5)

# Tine dimensions
total_tines = 18
total_tine_width = 16.0
tine_width = total_tine_width / total_tines

# Pins
num_pins        = total_tines
pin_radial_bump = 0.5   # how far each pin extends radially beyond the cassette OD
pin_width       = tine_width / 2
pin_height      = tine_width / 2
pin_vertical_offset = 1.0

# Base ring dimensions
base_ring_height = 1.8  # mm (from Z=0..1.8)
base_ring_od     = 15.0 # mm outer diameter
base_ring_id     = 5.0  # mm inner diameter

# 1) BUILD THE BASE RING (OD=15 mm, ID=5 mm, height=1.8 mm, Z=0..1.8)
base_ring = (
    cq.Workplane("XY")
    .circle(base_ring_od / 2.0)    # outer radius 7.5
    .extrude(base_ring_height)     # from Z=0..1.8
    .cut(
        cq.Workplane("XY")
        .circle(base_ring_id / 2.0)  # inner radius 2.5
        .extrude(base_ring_height)
    )
)

# 2) BUILD THE MAIN CASSETTE (OD=13 mm, ID=5 mm, height=20 mm, Z=0..20)
outer_cylinder = (
    cq.Workplane("XY")
    .workplane(offset=base_ring_height)
    .circle(cassette_radius)            # e.g. 6.5 mm
    .extrude(cassette_total_height)     # from Z=0..20
)

inner_cylinder = (
    cq.Workplane("XY")
    .workplane(offset=base_ring_height)
    .circle(cassette_radius - cassette_wall_thickness)  # 6.5 - 4 = 2.5 mm
    .extrude(cassette_total_height)                     # from Z=0..20
)

cassette_body = outer_cylinder.cut(inner_cylinder)

# Pins
pins = cq.Workplane("XY")

z_min = base_ring_height + pin_vertical_offset

for i in range(num_pins):
    angle_deg = i * (360.0 / num_pins)
    angle_rad = math.radians(angle_deg)

    centre_offset = pin_width / 2
    spacing_offset = tine_width * i
    z_pin_center = z_min + spacing_offset + centre_offset

    # Place the pin on the cassette's outer radius in X/Y
    x_center = cassette_radius * math.cos(angle_rad)
    y_center = cassette_radius * math.sin(angle_rad)

    # The pin is a small box extruding radially outward
    z_bottom = z_pin_center - (pin_height / 2.0)

    single_pin = (
        cq.Workplane("XY")
        .box(
            length=pin_radial_bump,  # 0.5 mm radial extension
            width=pin_width,         # 0.5 mm wide tangentially
            height=pin_height,       # 1.0 mm tall
            centered=(False, True, False)
        )
        .rotate((0, 0, 0), (0, 0, 1), angle_deg)
        .translate((x_center, y_center, z_bottom))
    )

    pins = pins.union(single_pin)

# Combine cassette body + pins + base ring
wheel_with_pins_and_base = cassette_body.union(pins).union(base_ring)

# --------------------------------------------------------------------------------
# PART 2: EXTENDED COG ASSEMBLY ON TOP
# --------------------------------------------------------------------------------

# Heights for stacked gears above cassette
big_cog_height    = 1.8  # mm
small_cog_height  = 1.5  # mm
top_circle_height = 0.7  # mm

# Total extension on top is ~4 mm (1.8 + 1.5 + 0.7)
big_cog_z_start   = base_ring_height + cassette_total_height         # starts at Z=21.8
big_cog_z_top     = big_cog_z_start + big_cog_height  # 23.3
small_cog_z_start = big_cog_z_top                 # 23.3
small_cog_z_top   = small_cog_z_start + small_cog_height  # 23.3
top_circle_z_start= small_cog_z_top               # 23.3
top_circle_z_top  = top_circle_z_start + top_circle_height # 24.0

# Large cog geometry (46 teeth)
big_cog_base_diam    = 17.0  # mm → base radius=8.5
big_cog_teeth_diam   = 20.0  # mm → teeth radius=10.0
num_teeth_big        = 46
big_cog_base_radius  = big_cog_base_diam / 2.0    # 8.5
big_cog_teeth_radius = big_cog_teeth_diam / 2.0   # 10.0
big_cog_radial_thick = big_cog_teeth_radius - big_cog_base_radius  # 1.5

# Small cog geometry (12 teeth)
small_cog_base_diam   = 5.0   # mm → radius=2.5
small_cog_teeth_diam  = 8.0   # mm → radius=4.0
num_teeth_small       = 12
small_cog_base_radius  = small_cog_base_diam / 2.0    # 2.5
small_cog_teeth_radius = small_cog_teeth_diam / 2.0   # 4.0
small_cog_radial_thick = small_cog_teeth_radius - small_cog_base_radius  # ~1.5

# Small top circle geometry
top_circle_diam   = 2.0  # mm → radius=1.0

# Helper functions to create 3D-tooth solids
def make_big_cog_tooth(radial_thickness, base_width, tip_width, tooth_height, fillet_3d=0.1):
    """
    Makes a trapezoidal "triangular" tooth in 2D, extrudes it, then fillets
    the vertical edges. Coordinates for the trapezoid:
        (0, -base_width/2) → (0, base_width/2)
        → (radial_thickness, tip_width/2) → (radial_thickness, -tip_width/2)
    """
    shape_2d = (
        cq.Workplane("XY")
        .polyline([
            (0, -base_width/2.0),
            (0,  base_width/2.0),
            (radial_thickness,  tip_width/2.0),
            (radial_thickness, -tip_width/2.0)
        ])
        .close()
    )
    tooth_3d = shape_2d.extrude(tooth_height)
    tooth_3d = tooth_3d.edges("|Z").fillet(fillet_3d)
    return tooth_3d

def make_small_cog_tooth(radial_thickness, tooth_width, tooth_height, fillet_3d=0.4):
    """
    Makes a rectangular tooth in 2D, extrudes it, then fillets all edges heavily.
    """
    shape_2d = (
        cq.Workplane("XY")
        .rect(radial_thickness, tooth_width, centered=(False, True))
    )
    tooth_3d = shape_2d.extrude(tooth_height)
    tooth_3d = tooth_3d.edges().fillet(fillet_3d)
    return tooth_3d

# 1) Base cylinders for each cog
big_cog_base = (
    cq.Workplane("XY")
    .workplane(offset=big_cog_z_start)  # offset=20
    .circle(big_cog_base_radius)        # 8.5 mm
    .extrude(big_cog_height)           # 1.8 mm tall
)

small_cog_base = (
    cq.Workplane("XY")
    .workplane(offset=small_cog_z_start)  # offset=21.8
    .circle(small_cog_base_radius)        # 2.5 mm
    .extrude(small_cog_height)           # 1.5 mm tall
)

# 2) Teeth for the large cog (triangular, small fillets)
big_cog_teeth = cq.Workplane("XY")

for i in range(num_teeth_big):
    angle_deg = i * (360.0 / num_teeth_big)
    angle_rad = math.radians(angle_deg)

    tooth_3d = make_big_cog_tooth(
        radial_thickness = big_cog_radial_thick,  # 1.5
        base_width       = 1.0,
        tip_width        = 0.4,
        tooth_height     = big_cog_height,        # 1.8
        fillet_3d        = 0.1
    )

    # Rotate & place so it merges at radius=8.5
    tooth_3d = (
        tooth_3d
        .rotate((0,0,0), (0,0,1), angle_deg)
        .translate((
            big_cog_base_radius * math.cos(angle_rad),
            big_cog_base_radius * math.sin(angle_rad),
            big_cog_z_start
        ))
    )
    big_cog_teeth = big_cog_teeth.union(tooth_3d)

big_cog = big_cog_base.union(big_cog_teeth)

# 3) Teeth for the small cog (rectangular, large 3D fillets)
small_cog_teeth = cq.Workplane("XY")

for i in range(num_teeth_small):
    angle_deg = i * (360.0 / num_teeth_small)
    angle_rad = math.radians(angle_deg)

    tooth_3d = make_small_cog_tooth(
        radial_thickness = small_cog_radial_thick,  # ~1.5
        tooth_width      = 1.0,
        tooth_height     = small_cog_height,        # 1.5
        fillet_3d        = 0.4
    )

    tooth_3d = (
        tooth_3d
        .rotate((0,0,0), (0,0,1), angle_deg)
        .translate((
            small_cog_base_radius * math.cos(angle_rad),
            small_cog_base_radius * math.sin(angle_rad),
            small_cog_z_start
        ))
    )
    small_cog_teeth = small_cog_teeth.union(tooth_3d)

small_cog = small_cog_base.union(small_cog_teeth)

# 4) Small top circle
top_circle = (
    cq.Workplane("XY")
    .workplane(offset=top_circle_z_start)  # 23.3
    .circle(top_circle_diam / 2.0)        # 1.0 mm radius
    .extrude(top_circle_height)           # 0.7 mm
)

# Combine entire assembly: cassette + ring + pins + large cog + small cog + top circle
full_assembly = (
    wheel_with_pins_and_base
    .union(big_cog)
    .union(small_cog)
    .union(top_circle)
)

# Export
full_assembly.val().exportStl("cassette.stl", tolerance=0.01)
print("Exported 'cassette.stl'.")